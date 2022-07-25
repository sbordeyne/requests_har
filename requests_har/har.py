import json
import pathlib
from cgi import parse_header
from collections import OrderedDict
from datetime import datetime
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlparse, ParseResult
from http.cookiejar import Cookie

from requests import PreparedRequest, Response, __version__ as requests_version

from requests_har import __version__


def has_http_only(cookie: Cookie) -> bool:
    extra_args = vars(cookie).get('_rest')
    for key in extra_args:
        if key.lower() == 'httponly':
            return True
    return False


def get_charset(headers: dict) -> str:
    header = headers.get('Content-Type', 'application/json; charset=utf-8')
    parsed = parse_header(header)
    if len(parsed) == 1:
        return 'utf-8'
    return parsed[1].get('charset', 'utf-8')


def format_query(url: str) -> list[dict[str, str]]:
    splits = urlsplit(url)
    query = splits.query
    parsed = parse_qsl(query)
    return [
        {'name': name, 'value': value, 'comment': ''}
        for name, value in parsed
    ]


def format_cookie(cookie: Cookie):
    return {
        'name': cookie.name,
        'value': cookie.value,
        'path': cookie.path,
        'domain': cookie.domain,
        'expires': datetime.fromtimestamp(cookie.expires).isoformat(),
        'secure': cookie.secure,
        'comment': cookie.comment,
    }


def format_header(name: str, value: str) -> dict[str, str]:
    return {
        'name': name,
        'value': value,
        'comment': '',
    }


def format_post_data(request: PreparedRequest):
    body = request.body
    if isinstance(body, bytes):
        charset = get_charset(request.headers)
        try:
            body = body.decode(charset)
        except UnicodeDecodeError:
            body = ''
    return {
        'mimeType': request.headers.get('Content-Type', 'application/json'),
        'params': [],
        'text': body,
    }


def get_header_size(headers: dict[str, str]) -> int:
    return len(
        '\n'.join(
            '%s: %s' % (header_name, header_value)
            for header_name, header_value in headers.items()
        )
    )


def format_response_content(response: Response) -> dict[str, int | str]:
    content = response.content
    if isinstance(content, bytes):
        charset = get_charset(response.headers)
        content = content.decode(charset)
    return {
        'size': len(response.content) if response.content is not None else -1,
        'mimeType': response.headers['Content-Type'],
        'text': content,
        'comment': '',
    }


def format_request(request: PreparedRequest, http_version: str) -> dict[str, Any]:
    data = {
        "method": request.method,
        "url": request.url,
        "httpVersion": http_version,
        "cookies": [format_cookie(cookie) for cookie in request._cookies],
        "headers": [
            format_header(name, value)
            for name, value in request.headers.items()
        ],
        "queryString": format_query(request.url),
        "headersSize": get_header_size(request.headers),
        "bodySize": len(request.body) if request.body is not None else -1,
        "comment": ""
    }
    if request.body:
        data['postData'] = format_post_data(request)
    return data


def format_response(response: Response, http_version: str) -> dict[str, Any]:
    data = {
        "status": response.status_code,
        "statusText": HTTPStatus(response.status_code).name,
        "httpVersion": http_version,
        "cookies": [format_cookie(cookie) for cookie in response.cookies],
        "headers": [
            format_header(name, value)
            for name, value in response.headers.items()
        ],
        "content": format_response_content(response),
        "redirectURL": response.headers.get('Location', ''),
        "headersSize": get_header_size(response.headers),
        "bodySize": len(response.content) if response.content is not None else -1,
        "comment": ""
    }
    return data


class HarDict(dict):
    '''
    Dictionnary tailored to hold requests and responses
    in order to later save it as an HTTP ARchive file.
    '''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self['log'] = {
            'version': '1.2',
            'creator': {
                "name": "requests-har",
                "version": __version__,
            },
            'browser': {
                "name": "requests",
                "version": requests_version,
            },
            'pages': [],
            'entries': [],
        }
        self.created_at = datetime.now().strftime("%Y%-m-%d_%H-%M-%S")
        self.filename: str | None = None

    def on_response(
        self, response: Response, timeout: int | None = None,
        verify: bool = True, proxies: OrderedDict = OrderedDict(),
        stream: bool = False, cert: str | None = None,
    ):
        '''
        Method designed to be used as a response hook
        for the python requests library

        On response, save the contents of the prepared request and the associated
        response to the HarDict object.
        '''
        if self.filename is None and response.request.url is not None:
            request_url: ParseResult = urlparse(response.request.url)
            self.filename = f'{self.created_at}_{request_url.netloc}.har'

        now = datetime.utcnow().isoformat(timespec='milliseconds')
        http_version: str = {
            10: "HTTP/1.0", 11: "HTTP/1.1"
        }.get(response.raw.version, 'HTTP/1.1')

        entry = {
            "startedDateTime": now,
            "time": 0,
            "request": format_request(response.request, http_version),
            "response": format_response(response, http_version),
            "cache": {
                "beforeRequest": None,
                "afterRequest": None,
            },
            "timings": {
                "send": 0,
                "wait": 0,
            },
            "_timeout": timeout,
            "_verify": verify,
            "_proxies": dict(proxies),
            "_stream": stream,
            "_cert": cert
        }
        self['log']['entries'].append(entry)

    def save(self, path: pathlib.Path):
        '''Saves the contents of this dict to the disk as JSON.'''
        filepath: pathlib.Path = path / self.filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as filepointer:
            json.dump(self, filepointer, indent=2)
