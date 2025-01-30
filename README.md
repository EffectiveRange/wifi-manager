# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                    |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| wifi\_event/\_\_init\_\_.py             |        1 |        0 |        0 |        0 |    100% |           |
| wifi\_event/wifiEvent.py                |       18 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/\_\_init\_\_.py           |        4 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/wifiControl.py            |       88 |        0 |       28 |        0 |    100% |           |
| wifi\_manager/wifiEventHandler.py       |      115 |        2 |       10 |        2 |     97% |91-93, 165->exit, 168->exit |
| wifi\_manager/wifiManager.py            |       70 |        0 |       24 |        2 |     98% |48->50, 96->exit |
| wifi\_manager/wifiWebServer.py          |      123 |        5 |       10 |        0 |     96% |80-82, 89-90 |
| wifi\_service/\_\_init\_\_.py           |        8 |        0 |        0 |        0 |    100% |           |
| wifi\_service/avahiService.py           |       22 |        0 |        2 |        0 |    100% |           |
| wifi\_service/dhcpcdService.py          |       36 |        0 |        4 |        2 |     95% |55->exit, 56->exit |
| wifi\_service/dnsmasqService.py         |       55 |        0 |        4 |        1 |     98% |    93->98 |
| wifi\_service/hostapdService.py         |       59 |        2 |        4 |        2 |     94% |30, 80, 102->exit |
| wifi\_service/networkManagerService.py  |       11 |        0 |        0 |        0 |    100% |           |
| wifi\_service/service.py                |      170 |        2 |       36 |        4 |     97% |121, 154->157, 166, 189->exit, 204->exit |
| wifi\_service/systemdResolvedService.py |       11 |        0 |        0 |        0 |    100% |           |
| wifi\_service/wpaService.py             |       80 |        1 |       16 |        5 |     94% |36, 110->exit, 112->exit, 125->127, 127->129 |
| wifi\_utility/\_\_init\_\_.py           |        5 |        0 |        0 |        0 |    100% |           |
| wifi\_utility/configLoader.py           |       25 |        0 |        2 |        0 |    100% |           |
| wifi\_utility/interfaceSelector.py      |       19 |        0 |        4 |        0 |    100% |           |
| wifi\_utility/serviceJournal.py         |       46 |        0 |        6 |        1 |     98% |    62->67 |
| wifi\_utility/ssdpServer.py             |       59 |        7 |       12 |        1 |     86% |34-39, 87->exit, 89-90 |
| wifi\_wpa/\_\_init\_\_.py               |        2 |        0 |        0 |        0 |    100% |           |
| wifi\_wpa/wpaConfig.py                  |       58 |        0 |       16 |        1 |     99% |    63->58 |
|                               **TOTAL** | **1085** |   **19** |  **178** |   **21** | **97%** |           |


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