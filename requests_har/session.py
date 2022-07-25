from requests import Session as RequestsSession

from requests_har.har import HarDict


class Session(RequestsSession):
    def __init__(self):
        super().__init__()
        self.har_dict = HarDict()
        self.hooks['response'].insert(0, self.har_dict.on_response)
