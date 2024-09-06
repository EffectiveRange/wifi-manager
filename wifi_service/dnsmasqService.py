# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import functools
from enum import Enum
from typing import Any

from common_utility import render_template_file, is_file_contains_lines, create_file
from context_logger import get_logger
from dbus import SystemBus

from wifi_event import WifiEventType
from wifi_service import ServiceDependencies, DhcpServerService

log = get_logger('DnsmasqService')


class DnsmasqPeerEvent(Enum):
    DhcpLeaseAdded = WifiEventType.HOTSPOT_PEER_CONNECTED
    DhcpLeaseUpdated = WifiEventType.HOTSPOT_PEER_RECONNECTED
    DhcpLeaseDeleted = WifiEventType.HOTSPOT_PEER_DISCONNECTED

    def __repr__(self) -> str:
        return self.name


class DnsmasqConfig(object):

    def __init__(self, interface: str, static_ip: str, dhcp_range: str, server_port: int) -> None:
        self.interface = interface
        self.static_ip = static_ip
        self.dhcp_range = dhcp_range
        self.server_port = server_port

    def to_dict(self) -> dict[str, Any]:
        return {
            'interface': self.interface,
            'hotspot_ip': self.static_ip,
            'dhcp_range': self.dhcp_range,
            'server_port': self.server_port,
        }


class DnsmasqService(DhcpServerService):
    _DNSMASQ_DBUS_SERVICE = 'uk.org.thekelleys.dnsmasq'
    _DNSMASQ_DBUS_PATH = '/uk/org/thekelleys/dnsmasq'
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/dnsmasq_2eservice'

    def __init__(
        self,
        dependencies: ServiceDependencies,
        system_bus: SystemBus,
        config: DnsmasqConfig,
        resource_root: str,
        template_file: str = 'config/dnsmasq.conf.template',
        config_file: str = '/etc/dnsmasq.conf',
    ) -> None:
        super().__init__('dnsmasq', self._SYSTEMD_DBUS_PATH, dependencies)
        self._system_bus = system_bus
        self._config_file = config_file
        self._config = config
        self._config_file_content = render_template_file(resource_root, template_file, config.to_dict())

    def get_supported_events(self) -> list[WifiEventType]:
        return [event.value for event in DnsmasqPeerEvent]

    def get_static_ip(self) -> str:
        return self._config.static_ip

    def _prepare_start(self) -> None:
        self._platform.execute_command(
            f'ifconfig {self._config.interface} {self._config.static_ip} netmask 255.255.255.0'
        )

    def _need_config_setup(self) -> bool:
        expected_config = self._config_file_content.splitlines()
        return not is_file_contains_lines(self._config_file, expected_config)

    def _setup_config(self) -> None:
        log.info('Creating service configuration file', service=self._name, file=self._config_file)
        create_file(self._config_file, self._config_file_content)

    def _setup_custom_event_handling(self) -> None:
        dbus_object = self._system_bus.get_object(self._DNSMASQ_DBUS_SERVICE, self._DNSMASQ_DBUS_PATH)
        for signal in DnsmasqPeerEvent:
            dbus_object.connect_to_signal(signal.name, functools.partial(self._on_dhcp_lease_changed, signal.value))

    def _on_dhcp_lease_changed(self, *args: Any) -> None:
        event_type = args[0]

        event_data = dict()
        if len(args) == 4:
            event_data['name'] = str(args[3])
            event_data['ip'] = str(args[1])
            event_data['mac'] = str(args[2])

        self._execute_callback(event_type, event_data)
