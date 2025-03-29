# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
from typing import Optional

from common_utility import is_file_matches_pattern
from context_logger import get_logger

from wifi_config import IWifiConfig, WifiNetwork

log = get_logger('WpaSupplicantConfig')


class WpaSupplicantConfig(IWifiConfig):
    NETWORK_START = 'network={'
    NETWORK_END = '}'

    def __init__(self, country: str, config_file: str = '/etc/wpa_supplicant/wpa_supplicant.conf') -> None:
        self._country = country
        self._config_file = config_file

    def get_config_file(self) -> str:
        return self._config_file

    def get_network(self, ssid: str) -> Optional[WifiNetwork]:
        return self._get_network_map().get(self._add_quotes(ssid), None)

    def get_networks(self) -> list[WifiNetwork]:
        return list(self._get_network_map().values())

    def add_network(self, network: WifiNetwork) -> None:
        network_map = self._get_network_map()

        network.ssid = self._add_quotes(network.ssid)
        network.password = self._add_quotes(network.password)

        network_map[network.ssid] = network

        self._save_networks_with_config(list(network_map.values()))

    def remove_network(self, ssid: str) -> None:
        network_map = self._get_network_map()

        network_map.pop(self._add_quotes(ssid), None)

        self._save_networks_with_config(list(network_map.values()))

    def need_config_file_setup(self) -> bool:
        pattern = '\n+'.join([f'({line})' for line in self._get_config_lines()])
        return not is_file_matches_pattern(self._config_file, pattern)

    def setup_config_file(self) -> None:
        self._save_networks_with_config(self.get_networks())

    def _get_config_lines(self) -> list[str]:
        return [
            'ctrl_interface=/run/wpa_supplicant',
            'update_config=1',
            'ap_scan=1',
            'bgscan=""',
            f'country={self._country}']

    def _strip_line(self, line: str) -> str:
        return line.strip().replace(' ', '')

    def _get_network_map(self) -> dict[str, WifiNetwork]:
        networks: dict[str, WifiNetwork] = {}

        if not os.path.exists(self._config_file):
            log.warn('Configuration file does not exist', file=self._config_file)
            return networks

        with open(self._config_file, 'r') as file:
            lines = file.readlines()

        current_network: Optional[WifiNetwork] = None
        for line in lines:
            stripped_line = self._strip_line(line)
            if stripped_line == self.NETWORK_START:
                current_network = WifiNetwork('', '', True, 0)
            elif stripped_line == self.NETWORK_END:
                if current_network is not None:
                    networks[self._add_quotes(current_network.ssid)] = current_network
                    current_network = None
            elif current_network is not None:
                self._populate_network(stripped_line, current_network)

        return networks

    def _populate_network(self, line: str, network: WifiNetwork) -> None:
        key_value = line.split('=')
        if key_value[0] == 'ssid':
            network.ssid = key_value[1]
        elif key_value[0] == 'psk':
            network.password = key_value[1]
        elif key_value[0] == 'disabled':
            network.enabled = not bool(int(key_value[1]))
        elif key_value[0] == 'priority':
            network.priority = int(key_value[1])

    def _save_networks_with_config(self, networks: list[WifiNetwork]) -> None:
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
        with open(self._config_file, 'w') as file:
            for line in self._get_config_lines():
                file.write(f'{line}\n')

            for network in networks:
                file.write(f'\n{self.NETWORK_START}\n')
                file.write(f'\tssid={network.ssid}\n')
                file.write(f'\tpsk={network.password}\n')
                file.write(f'\tdisabled={int(not network.enabled)}\n')
                file.write(f'\tpriority={network.priority}\n')
                file.write(f'{self.NETWORK_END}\n')

    def _add_quotes(self, value: str) -> str:
        return value if value.startswith('"') else f'"{value}"'
