# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from typing import Optional


@dataclass
class WifiNetwork(object):
    ssid: str
    password: str
    enabled: bool
    priority: int


class IWifiConfig(object):

    def get_config_file(self) -> str:
        raise NotImplementedError()

    def get_network(self, ssid: str) -> Optional[WifiNetwork]:
        raise NotImplementedError()

    def get_networks(self) -> list[WifiNetwork]:
        raise NotImplementedError()

    def add_network(self, network: WifiNetwork) -> None:
        raise NotImplementedError()

    def remove_network(self, ssid: str) -> None:
        raise NotImplementedError()

    def need_config_file_setup(self) -> bool:
        raise NotImplementedError()

    def setup_config_file(self) -> None:
        raise NotImplementedError()
