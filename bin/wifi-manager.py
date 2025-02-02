#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, BooleanOptionalAction
from pathlib import Path
from signal import signal, SIGINT, SIGTERM
from threading import Thread
from typing import Any

from _dbus_glib_bindings import DBusGMainLoop
from common_utility import ReusableTimer
from context_logger import setup_logging, get_logger
from cysystemd.reader import JournalReader  # type: ignore
from dbus import SystemBus
from gi.repository import GLib
from jinja2 import Template
from systemd_dbus import SystemdDbus

from wifi_manager import WifiControl, WifiEventHandler, WebServerConfig, WifiWebServer, WifiManager
from wifi_service import (
    WpaService,
    DhcpcdService,
    AvahiService,
    HostapdService,
    DnsmasqService,
    HostapdConfig,
    DnsmasqConfig,
    IService,
    ServiceDependencies,
    NetworkManagerService,
    SystemdResolvedService,
)
from wifi_utility import Platform, ConfigLoader, WlanInterfaceSelector, SsdpServer, ServiceJournal
from wifi_wpa import WpaDbus, WpaConfig

APPLICATION_NAME = 'wifi-manager'

log = get_logger('WifiManagerApp')


def main() -> None:
    resource_root = _get_resource_root()
    arguments = _get_arguments()

    setup_logging(APPLICATION_NAME, log_file_path=arguments['log_file'])

    log.info('Started wifi-manager', arguments=arguments)

    configuration = ConfigLoader(resource_root).load(arguments)

    _update_logging(arguments, configuration)

    log.info('Retrieved configuration', configuration=configuration)

    try:
        interface = configuration['interface']
        device_role = configuration['device_role']
        hostname_pattern = configuration['hostname_pattern']
        password = configuration['password']
        client_timeout = int(configuration['client_timeout'])
        peer_timeout = int(configuration['peer_timeout'])
        hotspot_ip = configuration['hotspot_ip']
        dhcp_range = configuration['dhcp_range']
        server_port = int(configuration['server_port'])
        country = configuration.get('country', 'HU')
        ssdp_enabled = configuration.get('ssdp_enabled', 'false').lower() == 'true'
        ssdp_usn_pattern = configuration['ssdp_usn_pattern']
        ssdp_st_pattern = configuration['ssdp_st_pattern']
    except KeyError as error:
        raise ValueError(f'Missing configuration key: {error}')

    platform = Platform()

    interface = WlanInterfaceSelector(platform).select(interface)

    platform.disable_wlan_power_save(interface)

    cpu_serial = platform.get_cpu_serial()
    mac_address = platform.get_mac_address(interface)

    id_context = {'device_role': device_role, 'cpu_serial': cpu_serial, 'mac_address': mac_address}

    hostname = Template(hostname_pattern).render(id_context)
    id_context['hostname'] = hostname

    system_bus = SystemBus(DBusGMainLoop(set_as_default=True))

    with SystemdDbus(system_bus) as systemd:
        wpa_config = WpaConfig(country)
        wpa_dbus = WpaDbus(interface, system_bus)
        dnsmasq_config = DnsmasqConfig(interface, hotspot_ip, dhcp_range, server_port)
        hostapd_config = HostapdConfig(interface, mac_address, hostname, password, country)
        reader = JournalReader()
        journal = ServiceJournal(reader)
        service_dependencies = ServiceDependencies(platform, systemd, journal)

        services: list[IService] = []

        network_manager_service = NetworkManagerService(service_dependencies)
        if network_manager_service.is_installed():
            services.append(network_manager_service)

        systemd_resolved_service = SystemdResolvedService(service_dependencies)
        if systemd_resolved_service.is_installed():
            services.append(systemd_resolved_service)

        dns_client_service = AvahiService(service_dependencies, hostname)
        dhcp_client_service = DhcpcdService(service_dependencies, system_bus, interface)
        dhcp_server_service = DnsmasqService(service_dependencies, system_bus, dnsmasq_config, resource_root)
        wifi_client_service = WpaService(service_dependencies, wpa_config, wpa_dbus, dhcp_client_service)
        wifi_hotspot_service = HostapdService(service_dependencies, hostapd_config, dhcp_server_service, resource_root)

        services.extend(
            [dns_client_service, dhcp_client_service, dhcp_server_service, wifi_client_service, wifi_hotspot_service]
        )

        timer = ReusableTimer()
        wifi_control = WifiControl(wifi_client_service, wifi_hotspot_service)
        ssdp_server = SsdpServer.create(ssdp_enabled, ssdp_usn_pattern, ssdp_st_pattern, id_context)
        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout, ssdp_server)
        web_server_config = WebServerConfig(hotspot_ip, server_port, resource_root)
        web_server = WifiWebServer(web_server_config, platform, event_handler)

        wifi_manager = WifiManager(services, wifi_control, event_handler, web_server, ssdp_server)

        def handler(signum: int, frame: Any) -> None:
            log.info('Shutting down wifi-manager', signum=signum)
            wifi_manager.shutdown()

        signal(SIGINT, handler)
        signal(SIGTERM, handler)

        event_loop = GLib.MainLoop()
        event_thread = Thread(target=event_loop.run)
        event_thread.start()

        wifi_manager.run()

        event_loop.quit()
        event_thread.join(1)


def _get_arguments() -> dict[str, Any]:
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('--config-file', help='configuration file', default='/etc/wifi-manager.conf')
    parser.add_argument(
        '--log-file', help='log file path', default='/var/log/effective-range/wifi-manager/wifi-manager.log'
    )
    parser.add_argument('--log-level', help='logging level')

    parser.add_argument('--hotspot-ip', help='hotspot static IP address')
    parser.add_argument('--password', help='hotspot Wi-Fi password')
    parser.add_argument('--dhcp-range', help='hotspot DHCP range')
    parser.add_argument('--server-port', help='web server port to listen on', type=int)
    parser.add_argument('--client-timeout', help='client timeout in seconds', type=int)
    parser.add_argument('--peer-timeout', help='peer timeout in seconds', type=int)
    parser.add_argument('--device-role', help='device role')
    parser.add_argument('--preferred-interface', help='preferred wlan interface')
    parser.add_argument('--hostname-pattern', help='hostname pattern')
    parser.add_argument('--country', help='country code')

    parser.add_argument('--ssdp-enabled', help='start optional SSDP server', action=BooleanOptionalAction)
    parser.add_argument('--ssdp-usn-pattern', help='SSDP USN pattern')
    parser.add_argument('--ssdp-st-pattern', help='SSDP service type pattern')

    return {k: v for k, v in vars(parser.parse_args()).items() if v is not None}


def _get_resource_root() -> str:
    return str(Path(os.path.dirname(__file__)).parent.absolute())


def _update_logging(arguments: dict[str, Any], configuration: dict[str, Any]) -> None:
    log_level = configuration.get('log_level', 'INFO')
    log_file = configuration['log_file']
    if log_level != 'INFO' or log_file != arguments['log_file']:
        setup_logging(APPLICATION_NAME, log_level, log_file, warn_on_overwrite=False)


if __name__ == '__main__':
    main()
