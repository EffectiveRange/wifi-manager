# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/EffectiveRange/wifi-manager/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                    |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|---------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| wifi\_event/\_\_init\_\_.py             |        1 |        0 |        0 |        0 |    100% |           |
| wifi\_event/wifiEvent.py                |       18 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/\_\_init\_\_.py           |        4 |        0 |        0 |        0 |    100% |           |
| wifi\_manager/wifiControl.py            |       88 |        0 |       28 |        0 |    100% |           |
| wifi\_manager/wifiEventHandler.py       |      111 |        2 |       10 |        2 |     97% |81-83, 148->exit, 151->exit |
| wifi\_manager/wifiManager.py            |       69 |        0 |       24 |        2 |     98% |48->50, 95->exit |
| wifi\_manager/wifiWebServer.py          |      120 |        3 |       26 |        8 |     92% |60->59, 79-81, 96->98, 97->96, 98->97, 125->124, 137->136, 148->147, 169->168 |
| wifi\_service/\_\_init\_\_.py           |        8 |        0 |        0 |        0 |    100% |           |
| wifi\_service/avahiService.py           |       22 |        0 |        4 |        2 |     92% |36->40, 37->36 |
| wifi\_service/dhcpcdService.py          |       36 |        0 |        4 |        2 |     95% |50->exit, 51->exit |
| wifi\_service/dnsmasqService.py         |       55 |        0 |        4 |        1 |     98% |    87->92 |
| wifi\_service/hostapdService.py         |       59 |        2 |        6 |        3 |     92% |26->25, 30, 75, 97->exit |
| wifi\_service/networkManagerService.py  |       11 |        0 |        0 |        0 |    100% |           |
| wifi\_service/service.py                |      170 |        2 |       36 |        4 |     97% |121, 154->157, 166, 189->exit, 204->exit |
| wifi\_service/systemdResolvedService.py |       11 |        0 |        0 |        0 |    100% |           |
| wifi\_service/wpaService.py             |       80 |        1 |       20 |        8 |     91% |32->31, 36, 92->98, 93->92, 105->exit, 107->exit, 120->122, 122->124 |
| wifi\_utility/\_\_init\_\_.py           |        7 |        0 |        0 |        0 |    100% |           |
| wifi\_utility/configLoader.py           |       25 |        0 |        2 |        0 |    100% |           |
| wifi\_utility/fileUtility.py            |       36 |        2 |       16 |        6 |     85% |17, 19->exit, 27->30, 37->exit, 42->exit, 49 |
| wifi\_utility/interfaceSelector.py      |       19 |        0 |        4 |        0 |    100% |           |
| wifi\_utility/serviceJournal.py         |       46 |        0 |        8 |        2 |     96% |28->27, 62->67 |
| wifi\_utility/ssdpServer.py             |       55 |        5 |       12 |        3 |     85% |30->29, 32-37, 62->64, 80->exit |
| wifi\_wpa/\_\_init\_\_.py               |        2 |        0 |        0 |        0 |    100% |           |
| wifi\_wpa/wpaConfig.py                  |       58 |        0 |       20 |        4 |     95% |54->57, 63->58, 88->exit, 89->88 |
|                               **TOTAL** | **1111** |   **17** |  **224** |   **47** | **95%** |           |


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