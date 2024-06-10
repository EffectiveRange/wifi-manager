# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import fileinput
import os.path
from enum import Enum
from typing import Any, Optional

from context_logger import get_logger

from wifi_event import WifiEventType
from wifi_service import WifiClientService, IService, ServiceDependencies
from wifi_utility import is_file_matches_pattern, delete_file
from wifi_wpa import IWpaDbus, IWpaConfig

log = get_logger('WpaService')


class WpaSupplicantEvent(Enum):
    interface_disabled = WifiEventType.CLIENT_DISABLED
    inactive = WifiEventType.CLIENT_INACTIVE
    scanning = WifiEventType.CLIENT_SCANNING
    associating = WifiEventType.CLIENT_CONNECTING
    completed = WifiEventType.CLIENT_CONNECTED
    disconnected = WifiEventType.CLIENT_DISCONNECTED

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def to_wifi_event(name: str) -> Optional['WifiEventType']:
        if name in WpaSupplicantEvent.__members__:
            return WpaSupplicantEvent[name].value
        else:
            return None


class WpaService(WifiClientService):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/wpa_5fsupplicant_2eservice'

    def __init__(self, dependencies: ServiceDependencies, wpa_config: IWpaConfig, wpa_dbus: IWpaDbus,
                 dhcp_client: IService,
                 service_file: str = '/lib/systemd/system/wpa_supplicant.service',
                 run_dir: str = '/run/wpa_supplicant') -> None:
        super().__init__('wpa_supplicant', self._SYSTEMD_DBUS_PATH, dependencies)
        self._wpa_config = wpa_config
        self._wpa_dbus = wpa_dbus
        self._dhcp_client = dhcp_client
        self._interface = wpa_dbus.get_interface()
        self._service_file = service_file
        self._run_file = os.path.join(run_dir, self._interface)

        config_file = self._wpa_config.get_config_file()
        self._exec_start = f'ExecStart=/sbin/{self._name} -u -s -O {run_dir} -i{self._interface} -c{config_file}\n'

    def get_supported_events(self) -> list[WifiEventType]:
        return [event.value for event in WpaSupplicantEvent]

    def get_interface(self) -> str:
        return self._interface

    def get_connected_ssid(self) -> Optional[str]:
        return self._wpa_dbus.get_current_network_ssid()

    def get_network_count(self) -> int:
        return len(self._wpa_config.get_networks())

    def get_networks(self) -> list[dict[str, Any]]:
        return list(self._wpa_config.get_networks().values())

    def add_network(self, network: dict[str, Any]) -> None:
        wpa_dbus_network = self._convert_to_wpa_dbus_network(network)

        if self.is_active():
            self._wpa_dbus.add_network(wpa_dbus_network)

        wpa_config_network = self._convert_to_wpa_config_network(wpa_dbus_network)

        self._wpa_config.add_network(wpa_config_network)

    def _prepare_start(self) -> None:
        self._platform.enable_wlan_interfaces()
        delete_file(self._run_file)
        self._dhcp_client.start()

    def _need_config_setup(self) -> bool:
        return not is_file_matches_pattern(self._service_file, self._exec_start)

    def _setup_config(self) -> None:
        log.info('Updating service file', file=self._service_file)

        with fileinput.FileInput(self._service_file, inplace=True) as file:
            for line in file:
                if 'ExecStart' in line:
                    line = self._exec_start
                print(line, end='')

        self._systemd.reload_daemon()

    def _setup_custom_event_handling(self) -> None:
        self._wpa_dbus.add_properties_changed_handler(self._on_wpa_properties_changed)

    def _on_wpa_properties_changed(self, properties: dict[str, Any]) -> None:
        state = properties.get('State')
        if state:
            event_type = WpaSupplicantEvent.to_wifi_event(state)
            if event_type:
                self._execute_callback(event_type, {})

    def _convert_to_wpa_dbus_network(self, network: dict[str, Any]) -> dict[str, Any]:
        return {
            'ssid': network['ssid'],
            'psk': network['password'],
            'disabled': int(not network['enabled']),
            'priority': network['priority']
        }

    def _convert_to_wpa_config_network(self, wpa_dbus_network: dict[str, Any]) -> dict[str, Any]:
        wpa_config_network = wpa_dbus_network.copy()
        if not str(wpa_dbus_network['ssid']).startswith('"'):
            wpa_config_network['ssid'] = f'"{wpa_dbus_network["ssid"]}"'
        if not str(wpa_dbus_network['psk']).startswith('"'):
            wpa_config_network['psk'] = f'"{wpa_dbus_network["psk"]}"'
        return wpa_config_network
