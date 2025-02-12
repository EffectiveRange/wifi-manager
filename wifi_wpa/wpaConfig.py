# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
from typing import Any, Optional

from common_utility import is_file_matches_pattern
from context_logger import get_logger

log = get_logger('WpaSupplicantConfig')


class IWpaConfig(object):

    def get_config_file(self) -> str:
        raise NotImplementedError()

    def get_network(self, ssid: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError()

    def get_networks(self) -> dict[str, dict[str, Any]]:
        raise NotImplementedError()

    def add_network(self, network: dict[str, Any]) -> None:
        raise NotImplementedError()

    def remove_network(self, ssid: str) -> None:
        raise NotImplementedError()

    def save_networks(self, networks: list[dict[str, Any]]) -> None:
        raise NotImplementedError()

    def need_config_file_setup(self) -> bool:
        raise NotImplementedError()

    def setup_config_file(self) -> None:
        raise NotImplementedError()


class WpaConfig(IWpaConfig):
    NETWORK_START = 'network={'
    NETWORK_END = '}'

    def __init__(self, country: str, config_file: str = '/etc/wpa_supplicant/wpa_supplicant.conf') -> None:
        self._country = country
        self._config_file = config_file

    def get_config_file(self) -> str:
        return self._config_file

    def get_network(self, ssid: str) -> Optional[dict[str, Any]]:
        return self.get_networks().get(ssid, None)

    def get_networks(self) -> dict[str, dict[str, Any]]:
        networks: dict[str, dict[str, Any]] = {}

        if not os.path.exists(self._config_file):
            log.warn('Configuration file does not exist', file=self._config_file)
            return networks

        with open(self._config_file, 'r') as file:
            lines = file.readlines()

        current_network: Optional[dict[str, Any]] = None
        for line in lines:
            stripped_line = self._strip_line(line)
            if self.NETWORK_START == stripped_line:
                current_network = {}
            elif self.NETWORK_END == stripped_line:
                if current_network is not None:
                    networks[str(current_network['ssid'])] = current_network
                    current_network = None
            elif current_network is not None:
                key_value = stripped_line.split('=')
                current_network[key_value[0]] = key_value[1]

        return networks

    def add_network(self, network: dict[str, Any]) -> None:
        networks = self.get_networks()

        networks[str(network['ssid'])] = network

        self.save_networks(list(networks.values()))

    def remove_network(self, ssid: str) -> None:
        networks = self.get_networks()

        networks.pop(ssid, None)

        self.save_networks(list(networks.values()))

    def save_networks(self, networks: list[dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
        with open(self._config_file, 'w') as file:
            for line in self._get_config_lines():
                file.write(f'{line}\n')

            for network in networks:
                file.write(f'\n{self.NETWORK_START}\n')
                for key, value in network.items():
                    file.write(f'\t{key}={value}\n')
                file.write(f'{self.NETWORK_END}\n')

    def need_config_file_setup(self) -> bool:
        pattern = '\n+'.join([f'({line})' for line in self._get_config_lines()])
        return not is_file_matches_pattern(self._config_file, pattern)

    def setup_config_file(self) -> None:
        networks = self.get_networks()

        self.save_networks(list(networks.values()))

    def _get_config_lines(self) -> list[str]:
        return [
            'ctrl_interface=/run/wpa_supplicant',
            'update_config=1',
            'ap_scan=1',
            'bgscan=""',
            f'country={self._country}']

    def _strip_line(self, line: str) -> str:
        return line.strip().replace(' ', '')
