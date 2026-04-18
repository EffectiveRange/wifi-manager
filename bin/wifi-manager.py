#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import gi

from arguments import APPLICATION_NAME, get_argument_parser
from wifi_connection import (
    ConnectionMonitorConfig,
    ConnectionMonitor,
    ConnectionAction,
)
from wifi_dbus import WpaSupplicantDbus, NetworkManagerDbus

gi.require_version('NM', '1.0')
import os
from pathlib import Path
from signal import signal, SIGINT, SIGTERM
from threading import Thread
from typing import Any

from _dbus_glib_bindings import DBusGMainLoop
from common_utility import ReusableTimer, ConfigLoader
from context_logger import setup_logging, get_logger
from cysystemd.reader import JournalReader  # type: ignore
from dbus import SystemBus

from gi.repository import GLib, NM
from jinja2 import Template
from systemd_dbus import SystemdDbus

from wifi_manager import (
    WifiControl,
    WifiEventHandler,
    WebServerConfig,
    WifiWebServer,
    WifiManager,
    WifiControlConfig,
)
from wifi_service import (
    WpaSupplicantService,
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
    WifiClientService,
)
from wifi_utility import (
    PlatformAccess,
    WlanInterfaceSelector,
    ServiceJournal,
    PlatformConfig,
    GpioBlinkDevice,
    BlinkConfig,
    BlinkControl,
)
from wifi_config import WpaSupplicantConfig, NetworkManagerConfig

log = get_logger('WifiManagerApp')

DEFAULT_CONFIG_PATH = Path(f'/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf.default')


def main() -> None:
    setup_logging(APPLICATION_NAME)

    resource_root = _get_resource_root()
    argument_parser = get_argument_parser()

    config = ConfigLoader(DEFAULT_CONFIG_PATH).load(argument_parser)

    setup_logging(APPLICATION_NAME, config.log_level, config.log_file, warn_on_overwrite=False)

    platform = PlatformAccess()
    wlan_interface = WlanInterfaceSelector(platform).select(config.wlan_interface)
    debian_12_or_higher = platform.get_platform_version() >= 12.0
    platform_config = PlatformConfig(platform, wlan_interface,
                                     '/boot/firmware/config.txt' if debian_12_or_higher else '/boot/config.txt')

    if platform_config.setup(config.wlan_disable_power_save, config.wlan_disable_roaming):
        log.warning('Platform configuration changed, reboot to apply changes')

    cpu_serial = platform.get_cpu_serial()
    mac_address = platform.get_mac_address(wlan_interface)

    id_context = {
        'device_role': config.device_role,
        'cpu_serial': cpu_serial,
        'mac_address': mac_address,
    }

    hostname = Template(config.device_hostname).render(id_context)
    id_context['hostname'] = hostname

    system_bus = SystemBus(DBusGMainLoop(set_as_default=True))

    with SystemdDbus(system_bus) as systemd:
        wpa_config = WpaSupplicantConfig(config.wlan_country)
        wpa_dbus = WpaSupplicantDbus(wlan_interface, system_bus)
        nm_client = NM.Client.new(None)
        nm_config = NetworkManagerConfig(wlan_interface, config.wlan_country)
        nm_dbus = NetworkManagerDbus(wlan_interface, nm_client)
        dnsmasq_config = DnsmasqConfig(
            wlan_interface, config.hotspot_static_ip, config.hotspot_dhcp_range, config.server_port
        )
        hostapd_config = HostapdConfig(
            wlan_interface,
            mac_address,
            hostname,
            config.hotspot_password,
            config.wlan_country,
            config.hotspot_startup_delay,
        )
        reader = JournalReader()
        journal = ServiceJournal(reader)
        service_dependencies = ServiceDependencies(platform, systemd, journal)

        services: dict[str, IService] = {}
        wifi_client_service: WifiClientService

        systemd_resolved_service = SystemdResolvedService(service_dependencies)
        dhcpcd_service = DhcpcdService(service_dependencies, system_bus, wlan_interface)
        avahi_service = AvahiService(service_dependencies, hostname)
        network_manager_service = NetworkManagerService(
            service_dependencies, nm_config, nm_dbus, config.client_restart_delay
        )
        dnsmasq_service = DnsmasqService(
            service_dependencies, system_bus, dnsmasq_config, resource_root
        )
        wpa_supplicant_service = WpaSupplicantService(
            service_dependencies, wpa_config, wpa_dbus, dhcpcd_service
        )
        hostapd_service = HostapdService(
            service_dependencies, hostapd_config, dnsmasq_service, resource_root
        )

        if debian_12_or_higher:
            _init_service(services, systemd_resolved_service, False)
            _init_service(services, dhcpcd_service, False)
            _init_service(services, avahi_service, True)
            _init_service(services, dnsmasq_service, True)
            _init_service(services, network_manager_service, True)
            _init_service(services, wpa_supplicant_service, True, False)
            _init_service(services, hostapd_service, True)

            wifi_client_service = network_manager_service
        else:
            _init_service(services, systemd_resolved_service, False)
            _init_service(services, dhcpcd_service, True)
            _init_service(services, avahi_service, True)
            _init_service(services, dnsmasq_service, True)
            _init_service(services, network_manager_service, False)
            _init_service(services, wpa_supplicant_service, True)
            _init_service(services, hostapd_service, True)

            wifi_client_service = wpa_supplicant_service

        wifi_hotspot_service = HostapdService(
            service_dependencies, hostapd_config, dnsmasq_service, resource_root
        )

        connection_monitor_timer = ReusableTimer()
        connection_connect_actions = config.connection_connect_actions.strip().split('\n')
        connection_restore_actions = config.connection_restore_actions.strip().split('\n')
        connect_actions = ConnectionAction.create_actions(
            connection_connect_actions, wifi_client_service, systemd, platform
        )
        restore_actions = ConnectionAction.create_actions(
            connection_restore_actions, wifi_client_service, systemd, platform
        )
        config_dir = Path(config.config).parent
        connection_monitor_config = ConnectionMonitorConfig(
            config_dir,
            config.connection_ping_interval,
            config.connection_ping_timeout,
            config.connection_ping_fail_limit,
            list(connect_actions),
            list(restore_actions)
        )

        connection_monitor = ConnectionMonitor(
            platform, systemd, connection_monitor_timer, connection_monitor_config
        )
        wifi_control_config = WifiControlConfig(config.control_switch_fail_limit, config.control_switch_fail_command)
        wifi_control = WifiControl(wifi_client_service, wifi_hotspot_service, platform, wifi_control_config)
        blink_config = BlinkConfig(
            config.identify_blink_frequency, config.identify_blink_interval, config.identify_blink_pause,
            config.identify_blink_count
        )
        blink_device = GpioBlinkDevice(
            config.identify_pin_gpio_number, active_high=config.identify_pin_active_high,
            initial_value=config.identify_pin_initial_value
        )
        blink_control = BlinkControl(blink_config, blink_device)
        event_handler_timer = ReusableTimer()
        event_handler = WifiEventHandler(
            wifi_control,
            blink_control,
            event_handler_timer,
            connection_monitor,
            config.client_timeout,
            config.hotspot_peer_timeout,
        )
        command_definitions = config.command_definitions.strip().split('\n')
        web_server_config = WebServerConfig(
            config.hotspot_static_ip, config.server_port, resource_root
        )
        web_server = WifiWebServer(web_server_config, platform, event_handler, command_definitions)

        wifi_manager = WifiManager(
            services, wifi_control, event_handler, connection_monitor, web_server
        )

        event_loop = GLib.MainLoop()
        event_thread = Thread(target=event_loop.run)

        def handler(signum: int, frame: Any) -> None:
            log.info('Shutting down wifi-manager', signum=signum)
            wifi_manager.shutdown()

            event_loop.quit()
            event_thread.join(1)

        signal(SIGINT, handler)
        signal(SIGTERM, handler)

        event_thread.start()

        wifi_manager.run()

        event_loop.quit()
        event_thread.join(1)


def _get_resource_root() -> str:
    return str(Path(os.path.dirname(__file__)).parent.absolute())


def _init_service(
        services: dict[str, IService],
        service: IService,
        is_required: bool,
        is_managed: bool = True,
) -> None:
    if service.is_installed():
        if is_required:
            if is_managed:
                services[service.get_name()] = service
        else:
            service.set_force_stop(True)
    else:
        if is_required:
            raise ValueError(f'Mandatory {service.get_name()} service is not installed')


if __name__ == '__main__':
    main()
