# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
from configparser import ConfigParser
from typing import Optional
from uuid import uuid4

from context_logger import get_logger

from wifi_config import IWifiConfig, WifiNetwork

log = get_logger('NetworkManagerConfig')


class NetworkManagerConfig(IWifiConfig):
    NETWORK_FILE_EXTENSION = '.nmconnection'

    def __init__(self, interface: str,
                 config_file: str = '/etc/NetworkManager/NetworkManager.conf',
                 network_dir: str = '/etc/NetworkManager/system-connections') -> None:
        self._interface = interface
        self._config_file = config_file
        self._network_dir = network_dir

    def get_config_file(self) -> str:
        return self._config_file

    def get_network(self, ssid: str) -> Optional[WifiNetwork]:
        file_name = self._get_network_file_name(ssid)

        if os.path.exists(file_name):
            return self._get_network_from_file(file_name)

        return None

    def get_networks(self) -> list[WifiNetwork]:
        return [self._get_network_from_file(f'{self._network_dir}/{file_name}') for file_name in
                os.listdir(self._network_dir) if file_name.endswith(self.NETWORK_FILE_EXTENSION)]

    def add_network(self, network: WifiNetwork) -> None:
        ssid = network.ssid
        password = network.password
        enabled = str(network.enabled).lower()
        priority = str(network.priority)

        config = ConfigParser(allow_no_value=True)

        file_name = self._get_network_file_name(ssid)

        if os.path.exists(file_name):
            log.info('Updating existing network configuration', ssid=ssid, file=file_name)

            config.read(file_name)
            config.set('connection', 'id', ssid)
            config.set('connection', 'autoconnect', enabled)
            config.set('connection', 'autoconnect-priority', priority)

            config.set('wifi', 'ssid', ssid)

            config.set('wifi-security', 'psk', password)
        else:
            log.info('Creating new network configuration', ssid=ssid, file=file_name)

            config.add_section('connection')
            config.set('connection', 'id', ssid)
            config.set('connection', 'uuid', str(uuid4()))
            config.set('connection', 'type', 'wifi')
            config.set('connection', 'interface-name', self._interface)
            config.set('connection', 'autoconnect', enabled)
            config.set('connection', 'autoconnect-priority', priority)

            config.add_section('wifi')
            config.set('wifi', 'mode', 'infrastructure')
            config.set('wifi', 'ssid', ssid)

            config.add_section('wifi-security')
            config.set('wifi-security', 'key-mgmt', 'wpa-psk')
            config.set('wifi-security', 'psk', password)

            config.add_section('ipv4')
            config.set('ipv4', 'method', 'auto')

            config.add_section('ipv6')
            config.set('ipv6', 'method', 'disabled')

        with open(file_name, 'w') as config_file:
            config.write(config_file)

        os.chmod(file_name, 0o600)

    def remove_network(self, ssid: str) -> None:
        file_name = self._get_network_file_name(ssid)

        if os.path.exists(file_name):
            os.remove(file_name)

    def need_config_file_setup(self) -> bool:
        return False

    def _get_network_file_name(self, ssid: str) -> str:
        return os.path.join(self._network_dir, f'{ssid}{self.NETWORK_FILE_EXTENSION}')

    def _get_network_from_file(self, file_name: str) -> WifiNetwork:
        config = ConfigParser(allow_no_value=True)
        config.read(file_name)

        ssid = config.get('wifi', 'ssid')
        password = config.get('wifi-security', 'psk', raw=True)
        enabled = config.get('connection', 'autoconnect', fallback='true') == 'true'
        priority = int(config.get('connection', 'autoconnect-priority', fallback='0'))

        return WifiNetwork(ssid, password, enabled, priority)
