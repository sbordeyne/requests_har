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
...
path = har_dict.save("/tmp/requests.har")  # If suffix is not .har, it will be set automatically.
```

You can also directly hook requests_har into a requests.request() call

```python
import requests
from requests_har.har import HarDict

har_dict = HarDict()

requests.get("https://google.com", hooks={"response": [har_dict.on_response]})
```

Or use the provided session if you don't need any other customization

```python
from requests_har.session import Session

session = Session()
session.headers["Accept"] = "application/json"  # Session() has the same interface as a classic requests.Session()
...
session.har_dict.save("/tmp/session.har")  # Save the HAR
```
