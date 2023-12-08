from requests_har.har import HarDict


def test_har_dict_is_dict_subclass():
    har_dict = HarDict()
    assert isinstance(har_dict, dict)
