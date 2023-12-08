"""
Module exposing a requests.Session subclass that records HTTP
requests and allows saving them to a HAR file.
"""

from requests import Session as RequestsSession

from requests_har.har import HarDict


class Session(RequestsSession):
    """
    requests.Session subclass that hooks an HarDict instance into
    the response hook.
    """

    def __init__(self):
        super().__init__()
        self.har_dict = HarDict()
        self.hooks["response"].insert(0, self.har_dict.on_response)
