# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from typing import Any

from common_utility import is_file_matches_pattern, append_file
from context_logger import get_logger
from dbus import SystemBus

from wifi_event import WifiEventType
from wifi_service import Service, ServiceDependencies

log = get_logger('DhcpcdService')


class DhcpcdService(Service):
    _DHCPCD_DBUS_SERVICE = 'name.marples.roy.dhcpcd'
    _DHCPCD_DBUS_PATH = '/name/marples/roy/dhcpcd'
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/dhcpcd_2eservice'

    def __init__(
        self,
        dependencies: ServiceDependencies,
        system_bus: SystemBus,
        interface: str,
        config_file: str = '/etc/dhcpcd.conf',
    ) -> None:
        super().__init__('dhcpcd', self._SYSTEMD_DBUS_PATH, dependencies)
        self._system_bus = system_bus
        self._interface = interface
        self._config_file = config_file

    def get_supported_events(self) -> list[WifiEventType]:
        return [WifiEventType.CLIENT_IP_ACQUIRED]

    def _prepare_start(self) -> None:
        self._platform.execute_command(f'ifconfig {self._interface} 0.0.0.0')

    def _need_config_setup(self) -> bool:
        pattern = f'(interface {self._interface})\n+(nohook wpa_supplicant)'
        return not is_file_matches_pattern(self._config_file, pattern)

    def _setup_config(self) -> None:
        log.info('Appending configuration file', file=self._config_file)
        configuration = f'interface {self._interface}\nnohook wpa_supplicant'
        append_file(self._config_file, f'\n{configuration}')

    def _setup_custom_event_handling(self) -> None:
        dbus_object = self._system_bus.get_object(self._DHCPCD_DBUS_SERVICE, self._DHCPCD_DBUS_PATH)
        dbus_object.connect_to_signal('Event', self._on_dhcpcd_event_signalled)

    def _on_dhcpcd_event_signalled(self, *args: Any) -> None:
        event_data = args[0]
        if isinstance(event_data, dict):
            if str(event_data.get('Interface')) == self._interface and str(event_data.get('Reason')) == 'BOUND':
                event_type = WifiEventType.CLIENT_IP_ACQUIRED
                self._execute_callback(event_type, {})
