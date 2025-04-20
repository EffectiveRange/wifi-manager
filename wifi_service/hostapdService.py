# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import time
from typing import Any

from common_utility import render_template_file, is_file_contains_lines, create_file
from context_logger import get_logger

from wifi_event import WifiEventType
from wifi_service import WifiHotspotService, ServiceDependencies, DhcpServerService, WifiHotspotStateEvent

log = get_logger('HostapdService')


class HostapdConfig(object):

    def __init__(self, interface: str, mac_address: str, ssid: str, password: str, country: str,
                 startup_delay: int) -> None:
        self.interface = interface
        self.mac_address = mac_address
        self.ssid = ssid
        self.password = password
        self.country = country
        self.startup_delay = startup_delay

    def to_dict(self) -> dict[str, Any]:
        return {
            'interface': self.interface,
            'mac_address': self.mac_address,
            'ssid': self.ssid,
            'password': self.password,
            'country': self.country,
        }


class HostapdService(WifiHotspotService):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/hostapd_2eservice'

    def __init__(
            self,
            dependencies: ServiceDependencies,
            config: HostapdConfig,
            dhcp_server: DhcpServerService,
            resource_root: str,
            template_file: str = 'config/hostapd.conf.template',
            config_file: str = '/etc/hostapd/hostapd.conf',
    ) -> None:
        super().__init__('hostapd', self._SYSTEMD_DBUS_PATH, dependencies)
        self._config_file = config_file
        self._config = config
        self._dhcp_server = dhcp_server
        self._configuration = render_template_file(resource_root, template_file, config.to_dict())
        self.set_auto_start(False)

    def start(self) -> None:
        self._dhcp_server.start()
        super().start()

    def restart(self) -> None:
        self._dhcp_server.restart()
        super().restart()

    def get_supported_events(self) -> set[WifiEventType]:
        return {event.value for event in WifiHotspotStateEvent}

    def get_interface(self) -> str:
        return self._config.interface

    def get_hotspot_ssid(self) -> str:
        return self._config.ssid

    def get_hotspot_ip(self) -> str:
        return self._dhcp_server.get_static_ip()

    def _prepare_start(self) -> None:
        self._platform.set_ip_address(self._config.interface, self._dhcp_server.get_static_ip())
        time.sleep(self._config.startup_delay)

    def _need_config_setup(self) -> bool:
        expected_config = self._configuration.splitlines()
        return not is_file_contains_lines(self._config_file, expected_config)

    def _setup_config(self) -> None:
        log.info('Creating service configuration file', service=self._name, file=self._config_file)
        create_file(self._config_file, self._configuration)

    def _on_service_state_changed(self, state: str) -> None:
        super()._on_service_state_changed(state)
        event_type = WifiHotspotStateEvent.to_wifi_event(state)
        if event_type:
            self._execute_callback(event_type, {})
