"""
Type definitions for requests_har
"""
from typing import Dict, List, Optional, TypedDict


class HARCookie(TypedDict):
    """
    Represents a cookie in a HAR file.
    """

    name: str
    value: Optional[str]
    path: str
    domain: str
    expires: str
    secure: bool
    comment: str


class HARHeader(TypedDict):
    """
    Represents a header in a HAR file.
    """

    name: str
    value: str
    comment: str


class HARQueryParam(TypedDict):
    """
    Represents a query parameter in a HAR file.
    """

    name: str
    value: str
    comment: str


class HARPostData(TypedDict):
    """
    Represents a POST body in a HAR file.
    """

    mimeType: str
    params: list[HARQueryParam]
    text: str


class HARRequest(TypedDict):
    """
    Represents a request in a HAR file.
    """

    method: str
    url: str
    httpVersion: str
    cookies: List[HARCookie]
    headers: List[HARHeader]
    queryString: List[HARQueryParam]
    postData: Optional[HARPostData]
    headersSize: int
    bodySize: int
    comment: str


class HARResponseContent(TypedDict):
    """
    Represents a response body in a HAR file.
    """

    size: int
    mimeType: str
    text: str
    comment: str


class HARResponse(TypedDict):
    """
    Represents a response in a HAR file.
    """

    status: int
    statusText: str
    httpVersion: str
    cookies: List[HARCookie]
    headers: List[HARHeader]
    content: HARResponseContent
    redirectURL: str
    headersSize: int
    bodySize: int
    comment: str


class HAREntryCache(TypedDict):
    """
    Represents the cache in an entry in a HAR file.
    """

    beforeRequest: Optional[str]
    afterRequest: Optional[str]


class HAREntryTimings(TypedDict):
    """
    Represents the timings in an entry in a HAR file.
    """

    send: float
    wait: float


class HAREntry(TypedDict):
    """
    Represents an entry in a HAR file.
    """

    startedDateTime: str
    time: float
    request: HARRequest
    response: HARResponse
    cache: HAREntryCache
    timings: HAREntryTimings
    _timeout: Optional[float]
    _verify: bool
    _proxies: Dict[str, str]
    _stream: bool
    _cert: Optional[str]


class HARLog(TypedDict):
    """
    Represents a log in a HAR file.
    """

    version: str
    creator: Dict[str, str]
    browser: Dict[str, str]
    pages: List[Dict[str, str]]
    entries: List[HAREntry]
    comment: str
