# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import fileinput
import os.path
from enum import Enum
from typing import Any, Optional

from common_utility import delete_file, is_file_matches_pattern
from context_logger import get_logger

from wifi_config import IWifiConfig, WifiNetwork
from wifi_dbus import IWifiDbus
from wifi_event import WifiEventType
from wifi_service import WifiClientService, IService, ServiceDependencies, WifiClientStateEvent

log = get_logger('WpaSupplicantService')


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


class WpaSupplicantService(WifiClientService):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/wpa_5fsupplicant_2eservice'

    def __init__(
            self,
            dependencies: ServiceDependencies,
            wifi_config: IWifiConfig,
            wifi_dbus: IWifiDbus,
            dhcp_client: IService,
            service_file: str = '/lib/systemd/system/wpa_supplicant.service',
            run_dir: str = '/run/wpa_supplicant',
    ) -> None:
        super().__init__('wpa_supplicant', self._SYSTEMD_DBUS_PATH, dependencies)
        self._wifi_config = wifi_config
        self._wifi_dbus = wifi_dbus
        self._dhcp_client = dhcp_client
        self._interface = wifi_dbus.get_interface()
        self._service_file = service_file
        self._run_file = os.path.join(run_dir, self._interface)

        config_file = self._wifi_config.get_config_file()
        self._exec_start = f'ExecStart=/sbin/{self._name} -u -s -O {run_dir} -i{self._interface} -c{config_file}\n'

    def get_supported_events(self) -> set[WifiEventType]:
        wpa_supplicant_events = {event.value for event in WpaSupplicantEvent}
        client_state_events = {event.value for event in WifiClientStateEvent}
        return wpa_supplicant_events.union(client_state_events)

    def get_interface(self) -> str:
        return self._interface

    def get_connected_ssid(self) -> Optional[str]:
        return self._wifi_dbus.get_active_ssid()

    def get_network_count(self) -> int:
        return len(self._wifi_config.get_networks())

    def get_networks(self) -> list[WifiNetwork]:
        return self._wifi_config.get_networks()

    def add_network(self, network: WifiNetwork) -> None:
        if self.is_active():
            self._wifi_dbus.add_network(network)

        self._wifi_config.add_network(network)

    def reset_wireless(self) -> None:
        self._wifi_dbus.reset_wireless()

    def _prepare_start(self) -> None:
        delete_file(self._run_file)
        self._dhcp_client.start()

    def _need_config_setup(self) -> bool:
        return self._need_service_file_setup() or self._wifi_config.need_config_file_setup()

    def _setup_config(self) -> None:
        if self._need_service_file_setup():
            log.info('Updating service file', file=self._service_file)

            with fileinput.FileInput(self._service_file, inplace=True) as file:
                for line in file:
                    if 'ExecStart' in line:
                        line = self._exec_start
                    print(line, end='')

            self._systemd.reload_daemon()

        if self._wifi_config.need_config_file_setup():
            log.info('Updating config file', file=self._wifi_config.get_config_file())
            self._wifi_config.setup_config_file()

    def _setup_custom_event_handling(self) -> None:
        self._wifi_dbus.add_connection_handler(self._on_wpa_properties_changed)

    def _need_service_file_setup(self) -> bool:
        return not is_file_matches_pattern(self._service_file, self._exec_start)

    def _on_service_state_changed(self, state: str) -> None:
        super()._on_service_state_changed(state)
        event_type = WifiClientStateEvent.to_wifi_event(state)
        if event_type:
            self._execute_callback(event_type, {})

    def _on_wpa_properties_changed(self, properties: dict[str, Any]) -> None:
        if state := properties.get('State'):
            if event_type := WpaSupplicantEvent.to_wifi_event(state):
                self._execute_callback(event_type, {})
