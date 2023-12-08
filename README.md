# requests_har

[![PyPI](https://img.shields.io/pypi/v/requests_har.svg)](https://pypi.python.org/pypi/requests_har)

HAR hook for the requests library

* Free software: MIT license

## How to use

Instanctiate `HarDict` and hook it into your requests session

```python
import requests
from requests_har.har import HarDict

har_dict: HarDict = HarDict()
session = requests.session()
session.hooks['response'].insert(0, har_dict.on_response)

```
