"""
Module containing the HarDict class and related
functions to parse requests and responses into
the HTTP archive format.
"""

import json
import pathlib
from email.message import EmailMessage
from collections import OrderedDict
from datetime import datetime
from http import HTTPStatus, cookiejar
from typing import Iterable, List, Optional, Union
from urllib.parse import parse_qsl, urlsplit

from requests import PreparedRequest, Response
from requests import __version__ as requests_version
from requests import structures

from requests_har.types import (
    HARCookie,
    HAREntry,
    HARHeader,
    HARLog,
    HARPostData,
    HARQueryParam,
    HARRequest,
    HARResponse,
    HARResponseContent,
)
from requests_har.version import __version__


def has_http_only(cookie: cookiejar.Cookie) -> bool:
    """
    Checks that a cookie has the HttpOnly flag set.

    :param cookie: The cookie to check
    :type cookie: cookiejar.Cookie
    :return: Whether the cookie has the HttpOnly flag set
    :rtype: bool
    """
    extra_args: List[str] = vars(cookie).get("_rest", [])
    for key in extra_args:
        if key.lower() == "httponly":
            return True
    return False


def get_charset(headers: structures.CaseInsensitiveDict[str]) -> str:
    """
    Returns the charset of the response from the response headers.

    :param headers: Headers dict
    :type headers: dict
    :return: Charset of the response
    :rtype: str
    """
    # alternative of cgi.parse_header() according to https://peps.python.org/pep-0594/#cgi
    m = EmailMessage()
    m['content-type'] = headers.get("Content-Type", "application/json; charset=utf-8")
    return m.get_content_charset('utf-8')


def format_query(url: str) -> List[HARQueryParam]:
    """
    Formats the query string of a URL into a list of dicts.

    :param url: URL to parse
    :type url: str
    :return: List of dicts representing the query string
    :rtype: list[dict[str, str]]
    """
    splits = urlsplit(url)
    query = splits.query
    parsed = parse_qsl(query)
    return [{"name": name, "value": value, "comment": ""} for name, value in parsed]


def format_cookie(cookie: cookiejar.Cookie) -> HARCookie:
    """
    Formats a cookie into a serializable dict.

    :param cookie: The cookie to format
    :type cookie: cookiejar.Cookie
    :return: The dict representing the cookie in the HAR format
    :rtype: ParsedCookie
    """
    expires = ""
    if cookie.expires:
        expires = datetime.fromtimestamp(cookie.expires).isoformat()

    return {
        "name": cookie.name,
        "value": cookie.value,
        "path": cookie.path,
        "domain": cookie.domain,
        "expires": expires,
        "secure": cookie.secure,
        "comment": cookie.comment or "",
    }


def format_header(name: str, value: str) -> HARHeader:
    """
    Formats a header into a serializable dict for the HAR format.

    :param name: Name of the header
    :type name: str
    :param value: Value of the header
    :type value: str
    :return: Dict representing the header in the HAR format
    :rtype: HARHeader
    """
    return {
        "name": name,
        "value": str(value),
        "comment": "",
    }


def decode_data(
    data: Union[memoryview, bytes, bytearray, str, None],
    charset: str = "utf-8",
) -> str:
    """
    Decodes data into a string based on the provided charset.

    :param data: The data to decode
    :type data: Union[memoryview, bytes, bytearray, str, None]
    :param charset: The charset to use when decoding the data
    :type charset: str
    :return: The decoded data
    :rtype: str
    """
    data_bytes: Optional[bytes] = None
    if isinstance(data, bytes):
        data_bytes = data
    elif isinstance(data, memoryview):
        data_bytes = data.tobytes()
    elif isinstance(data, bytearray):
        data_bytes = bytes(data)
    elif isinstance(data, str):
        return data
    elif data is None:
        return ""
    if data_bytes is None:
        raise ValueError("data must be a bytes-like object")
    try:
        return data_bytes.decode(charset)
    except UnicodeDecodeError:
        return ""


def format_post_data(request: PreparedRequest) -> HARPostData:
    """
    Formats a POST request's body into a serializable dict for the HAR format.

    :param request: _description_
    :type request: PreparedRequest
    :return: _description_
    :rtype: _type_
    """
    charset = get_charset(request.headers)
    body = decode_data(request.body, charset)
    return {
        "mimeType": request.headers.get("Content-Type", "application/json"),
        "params": [],
        "text": body,
    }


def get_header_size(headers: structures.CaseInsensitiveDict[str]) -> int:
    """
    Computes the length of the headers.

    :param headers: Headers dictionary
    :type headers: dict[str, str]
    :return: Length of the headers joined by newlines
    :rtype: int
    """
    return len(
        "\n".join(
            f"{header_name}: {header_value}"
            for header_name, header_value in headers.items()
        )
    )


def format_response_content(response: Response) -> HARResponseContent:
    """
    Parses the response content using the charset from the response headers.
    Then formats the response content into a serializable dict for the HAR format.
    The size is computed from the length of the content.
    mimeType is taken from the Content-Type header.

    :param response: _description_
    :type response: Response
    :return: _description_
    :rtype: HARResponseContent
    """
    charset = get_charset(response.headers)
    content = decode_data(response.content, charset)

    return {
        "size": len(response.content) if response.content is not None else -1,
        "mimeType": response.headers["Content-Type"],
        "text": content,
        "comment": "",
    }


def format_request(request: PreparedRequest, http_version: str) -> HARRequest:
    """
    Formats a request into the HAR format.

    :param request: The request from the `requests` library
    :type request: PreparedRequest
    :param http_version: HTTP version of the request
    :type http_version: str
    :return: The serialized request in the HAR format
    :rtype: HARRequest
    """
    cookie_jar: Iterable[cookiejar.Cookie] = getattr(request, "_cookies", [])
    data: HARRequest = {
        "method": request.method or "GET",
        "url": request.url or "",
        "httpVersion": http_version,
        "cookies": [format_cookie(cookie) for cookie in cookie_jar],
        "headers": [
            format_header(name, value) for name, value in request.headers.items()
        ],
        "queryString": format_query(request.url or ""),
        "headersSize": get_header_size(request.headers),
        "bodySize": len(request.body) if request.body is not None else -1,
        "comment": "",
        "postData": None,
    }
    if request.body:
        data["postData"] = format_post_data(request)
    return data


def format_response(response: Response, http_version: str) -> HARResponse:
    """
    Formats a response from the `requests` library into the HAR format.

    :param response: The response to format
    :type response: Response
    :param http_version: The HTTP version used when making the request
    :type http_version: str
    :return: The serialized response in the HAR format
    :rtype: HARResponse
    """
    return {
        "status": response.status_code,
        "statusText": HTTPStatus(response.status_code).name,
        "httpVersion": http_version,
        "cookies": [format_cookie(cookie) for cookie in response.cookies],
        "headers": [
            format_header(name, value) for name, value in response.headers.items()
        ],
        "content": format_response_content(response),
        "redirectURL": response.headers.get("Location", ""),
        "headersSize": get_header_size(response.headers),
        "bodySize": len(response.content) if response.content is not None else -1,
        "comment": "",
    }


class HarDict(dict):
    """
    Dictionnary tailored to hold requests and responses
    in order to later save it as an HTTP ARchive file.
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self["log"]: HARLog = {
            "version": "1.2",
            "creator": {
                "name": "requests-har",
                "version": __version__,
            },
            "browser": {
                "name": "requests",
                "version": requests_version,
            },
            "pages": [],
            "entries": [],
        }
        self.created_at = datetime.now().strftime("%Y%-m-%d_%H-%M-%S")

    def on_response(
        self,
        response: Response,
        timeout: int | None = None,
        verify: bool = True,
        proxies: Optional[OrderedDict] = None,
        stream: bool = False,
        cert: str | None = None,
    ):  # pylint: disable=too-many-arguments
        """
        Method designed to be used as a response hook
        for the python requests library

        On response, save the contents of the prepared request and the associated
        response to the HarDict object.
        """
        proxies = proxies or OrderedDict()

        now = datetime.utcnow().isoformat(timespec="milliseconds")
        http_version: str = {10: "HTTP/1.0", 11: "HTTP/1.1"}.get(
            response.raw.version, "HTTP/1.1"
        )

        entry: HAREntry = {
            "startedDateTime": now,
            "time": 0,
            "request": format_request(response.request, http_version),
            "response": format_response(response, http_version),
            "cache": {
                "beforeRequest": None,
                "afterRequest": None,
            },
            "timings": {
                "send": response.elapsed.total_seconds(),
                # Requests is synchronous, so this is always 0, we don't wait for other requests
                "wait": 0,
            },
            "_timeout": timeout,
            "_verify": verify,
            "_proxies": dict(proxies),
            "_stream": stream,
            "_cert": cert,
        }
        self["log"]["entries"].append(entry)

    def save(self, path: Union[pathlib.Path, str], encoding="utf-8") -> pathlib.Path:
        """Saves the contents of this dict to the disk as JSON."""
        path = pathlib.Path(path)

        if path.is_dir():
            raise ValueError("path must be a file, not a directory")

        if path.suffix != ".har":
            path = path.with_suffix(".har")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self, indent=2), encoding=encoding)
        return path
