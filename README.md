# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| wifi\_config/\_\_init\_\_.py          |        3 |        0 |        0 |        0 |    100% |           |
| wifi\_config/nmConfig.py              |       74 |        0 |        6 |        1 |     99% |  96->exit |
| wifi\_config/wifiConfig.py            |       12 |        0 |        0 |        0 |    100% |           |
| wifi\_config/wsConfig.py              |       80 |        0 |       24 |        2 |     98% |84->79, 100->exit |
| wifi\_connection/\_\_init\_\_.py      |        2 |        0 |        0 |        0 |    100% |           |
| wifi\_connection/connectionAction.py  |       60 |        1 |       16 |        3 |     95% |30, 45->40, 50->40 |
| wifi\_connection/connectionMonitor.py |       44 |        0 |       12 |        0 |    100% |           |
| wifi\_dbus/\_\_init\_\_.py            |        3 |        0 |        0 |        0 |    100% |           |
| wifi\_dbus/nmDbus.py                  |       71 |        0 |       14 |        2 |     98% |53->57, 94->exit |
| wifi\_dbus/wifiDbus.py                |       21 |        0 |        0 |        0 |    100% |           |
| wifi\_event/\_\_init\_\_.py           |        1 |        0 |        0 |        0 |    100% |           |
| wifi\_event/wifiEvent.py              |       19 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/\_\_init\_\_.py         |        4 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/wifiControl.py          |      112 |        0 |       30 |        0 |    100% |           |
| wifi\_manager/wifiEventHandler.py     |      129 |        0 |        8 |        1 |     99% | 137->exit |
| wifi\_manager/wifiManager.py          |       66 |        2 |       18 |        0 |     98% |     93-94 |
| wifi\_manager/wifiWebServer.py        |      166 |        5 |       10 |        0 |     97% |99-101, 108-109 |
| wifi\_service/\_\_init\_\_.py         |        8 |        0 |        0 |        0 |    100% |           |
| wifi\_service/avahiService.py         |       28 |        3 |        6 |        1 |     82% |     48-50 |
| wifi\_service/dhcpcdService.py        |       36 |        0 |        4 |        2 |     95% |55->exit, 56->exit |
| wifi\_service/dnsmasqService.py       |       54 |        0 |        4 |        1 |     98% |    89->94 |
| wifi\_service/hostapdService.py       |       55 |        1 |        2 |        1 |     96% |70, 93->exit |
| wifi\_service/nmService.py            |       71 |        4 |        6 |        2 |     90% |49, 96-99, 107->exit |
| wifi\_service/resolvedService.py      |        8 |        0 |        0 |        0 |    100% |           |
| wifi\_service/service.py              |      206 |       12 |       40 |        8 |     91% |121, 141, 160-162, 177->180, 189, 212->exit, 227->exit, 238->exit, 249-250, 275-278, 294 |
| wifi\_service/wsService.py            |       83 |        5 |       18 |        4 |     89% |37, 97->108, 119-122, 125->exit, 126->exit |
| wifi\_utility/\_\_init\_\_.py         |        6 |        0 |        0 |        0 |    100% |           |
| wifi\_utility/blinkControl.py         |       41 |        0 |        6 |        0 |    100% |           |
| wifi\_utility/interfaceSelector.py    |       19 |        0 |        4 |        0 |    100% |           |
| wifi\_utility/platformConfig.py       |       60 |        0 |       14 |        1 |     99% |  91->exit |
| wifi\_utility/serviceJournal.py       |       46 |        0 |        6 |        1 |     98% |    62->67 |
| **TOTAL**                             | **1588** |   **33** |  **248** |   **30** | **96%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/EffectiveRange/wifi-manager/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/EffectiveRange/wifi-manager/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FEffectiveRange%2Fwifi-manager%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.