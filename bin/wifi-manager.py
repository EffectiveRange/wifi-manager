#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import pathlib

import gi

from wifi_connection import (
    ConnectionMonitorConfig,
    ConnectionMonitor,
    ConnectionRestoreAction,
)
from wifi_dbus import WpaSupplicantDbus, NetworkManagerDbus

gi.require_version("NM", "1.0")
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
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
    WifiManager, WifiControlConfig,
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

APPLICATION_NAME = "wifi-manager"

log = get_logger("WifiManagerApp")


def main() -> None:
    resource_root = _get_resource_root()
    arguments = _get_arguments()

    setup_logging(APPLICATION_NAME)

    log.info(f"Started {APPLICATION_NAME}", arguments=arguments)

    config = ConfigLoader(Path(f"{resource_root}/config/{APPLICATION_NAME}.conf.default")).load(arguments)

    _update_logging(arguments, config)

    log.info("Retrieved configuration", configuration=config)

    try:
        api_server_port = int(config.get("api_server_port", 8080))
        device_role = config.get("device_role", "edge")
        device_hostname = config.get("device_hostname", "er-{{device_role}}-{{cpu_serial}}")
        wlan_interface = config.get("wlan_interface", "wlan0")
        wlan_country = config.get("wlan_country", "HU")
        disable_power_save = config.get("wlan_disable_power_save", False)
        disable_roaming = config.get("wlan_disable_roaming", False)
        switch_fail_limit = int(config.get("control_switch_fail_limit", 5))
        switch_fail_command = config.get("control_switch_fail_command", "reboot")
        client_timeout = int(config.get("client_timeout", 15))
        client_restart_delay = int(config.get("client_restart_delay", 5))
        hotspot_password = config.get("hotspot_password", "p4ssw0rd")
        hotspot_peer_timeout = int(config.get("hotspot_peer_timeout", 120))
        hotspot_static_ip = config.get("hotspot_static_ip", "192.168.100.1")
        hotspot_dhcp_range = config.get("hotspot_dhcp_range", "192.168.100.2,192.168.100.254,255.255.255.0,2m")
        hotspot_startup_delay = int(config.get("hotspot_startup_delay", 5))
        connection_ping_interval = int(config.get("connection_ping_interval", 60))
        connection_ping_timeout = int(config.get("connection_ping_timeout", 5))
        connection_ping_fail_limit = int(config.get("connection_ping_fail_limit", 5))
        connection_restore_actions = config.get(
            "connection_restore_actions", "reset-wireless"
        ).split("\n")
        identify_pin_gpio_number = int(config.get("identify_pin_gpio_number", 12))
        identify_pin_active_high = config.get("identify_pin_active_high", True)
        identify_pin_initial_value = config.get("identify_pin_initial_value", False)
        identify_blink_frequency = float(config.get("identify_blink_frequency", 440))
        identify_blink_interval = float(config.get("identify_blink_interval", 0.5))
        identify_blink_pause = float(config.get("identify_blink_pause", 0.5))
        identify_blink_count = int(config.get("identify_blink_count", 3))
    except KeyError as error:
        raise ValueError(f"Missing configuration key: {error}")

    platform = PlatformAccess()
    wlan_interface = WlanInterfaceSelector(platform).select(wlan_interface)
    debian_12_or_higher = platform.get_platform_version() >= 12.0
    platform_config = PlatformConfig(platform, wlan_interface,
                                     "/boot/firmware/config.txt" if debian_12_or_higher else "/boot/config.txt")

    if platform_config.setup(disable_power_save, disable_roaming):
        log.warning("Platform configuration changed, reboot to apply changes")

    cpu_serial = platform.get_cpu_serial()
    mac_address = platform.get_mac_address(wlan_interface)

    id_context = {
        "device_role": device_role,
        "cpu_serial": cpu_serial,
        "mac_address": mac_address,
    }

    hostname = Template(device_hostname).render(id_context)
    id_context["hostname"] = hostname

    system_bus = SystemBus(DBusGMainLoop(set_as_default=True))

    with SystemdDbus(system_bus) as systemd:
        wpa_config = WpaSupplicantConfig(wlan_country)
        wpa_dbus = WpaSupplicantDbus(wlan_interface, system_bus)
        nm_client = NM.Client.new(None)
        nm_config = NetworkManagerConfig(wlan_interface, wlan_country)
        nm_dbus = NetworkManagerDbus(wlan_interface, nm_client)
        dnsmasq_config = DnsmasqConfig(
            wlan_interface, hotspot_static_ip, hotspot_dhcp_range, api_server_port
        )
        hostapd_config = HostapdConfig(
            wlan_interface,
            mac_address,
            hostname,
            hotspot_password,
            wlan_country,
            hotspot_startup_delay,
        )
        reader = JournalReader()
        journal = ServiceJournal(reader)
        service_dependencies = ServiceDependencies(platform, systemd, journal)

        services: list[IService] = []
        wifi_client_service: WifiClientService

        systemd_resolved_service = SystemdResolvedService(service_dependencies)
        dhcpcd_service = DhcpcdService(service_dependencies, system_bus, wlan_interface)
        avahi_service = AvahiService(service_dependencies, hostname)
        network_manager_service = NetworkManagerService(
            service_dependencies, nm_config, nm_dbus, client_restart_delay
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
        restore_actions = ConnectionRestoreAction.create_actions(
            connection_restore_actions, wifi_client_service, systemd, platform
        )
        connection_monitor_config = ConnectionMonitorConfig(
            connection_ping_interval,
            connection_ping_timeout,
            connection_ping_fail_limit,
            list(restore_actions),
        )

        connection_monitor = ConnectionMonitor(
            platform, connection_monitor_timer, connection_monitor_config
        )
        wifi_control_config = WifiControlConfig(switch_fail_limit, switch_fail_command)
        wifi_control = WifiControl(wifi_client_service, wifi_hotspot_service, platform, wifi_control_config)
        blink_config = BlinkConfig(
            identify_blink_frequency, identify_blink_interval, identify_blink_pause, identify_blink_count
        )
        blink_device = GpioBlinkDevice(
            identify_pin_gpio_number, active_high=identify_pin_active_high, initial_value=identify_pin_initial_value
        )
        blink_control = BlinkControl(blink_config, blink_device)
        event_handler_timer = ReusableTimer()
        event_handler = WifiEventHandler(
            wifi_control,
            blink_control,
            event_handler_timer,
            connection_monitor,
            client_timeout,
            hotspot_peer_timeout,
        )
        web_server_config = WebServerConfig(
            hotspot_static_ip, api_server_port, resource_root
        )
        web_server = WifiWebServer(web_server_config, platform, event_handler)

        wifi_manager = WifiManager(
            services, wifi_control, event_handler, connection_monitor, web_server
        )

        event_loop = GLib.MainLoop()
        event_thread = Thread(target=event_loop.run)

        def handler(signum: int, frame: Any) -> None:
            log.info("Shutting down wifi-manager", signum=signum)
            wifi_manager.shutdown()

            event_loop.quit()
            event_thread.join(1)

        signal(SIGINT, handler)
        signal(SIGTERM, handler)

        event_thread.start()

        wifi_manager.run()

        event_loop.quit()
        event_thread.join(1)


def _get_arguments() -> dict[str, Any]:
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    default_config = f"/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf"
    parser.add_argument(
        "-c",
        "--config-file",
        help="configuration file",
        default=default_config,
    )

    parser.add_argument("-f", "--log-file", help="log file path")
    parser.add_argument("-l", "--log-level", help="logging level")

    parser.add_argument(
        "--api-server-port", help="web server port to listen on", type=int
    )

    parser.add_argument("--device-role", help="device role")
    parser.add_argument("--device-hostname", help="hostname pattern")

    parser.add_argument("--wlan-interface", help="preferred wlan interface")
    parser.add_argument("--wlan-country", help="country code")
    parser.add_argument("--wlan-disable-power-save", help="disable wlan power save mode",
                        action="store_true", default=False)
    parser.add_argument("--wlan-disable-roaming", help="disable wifi roaming",
                        action="store_true", default=False)

    parser.add_argument("--control-switch-fail-limit", help="mode switching failure limit", type=int)
    parser.add_argument("--control-switch-fail-command", help="command to execute when reaching failure limit")

    parser.add_argument("--client-timeout", help="client timeout in seconds", type=int)
    parser.add_argument("--client-restart-delay", help="client restart delay in seconds", type=int)

    parser.add_argument("--hotspot-password", help="hotspot Wi-Fi password")
    parser.add_argument(
        "--hotspot-peer-timeout", help="peer timeout in seconds", type=int
    )
    parser.add_argument("--hotspot-static-ip", help="hotspot static IP address")
    parser.add_argument("--hotspot-dhcp-range", help="hotspot DHCP range")
    parser.add_argument(
        "--hotspot-startup-delay", help="hotspot startup delay in seconds", type=int
    )

    args = parser.parse_args()
    if (
            args.config_file == default_config
            and not pathlib.Path(args.config_file).exists()
    ):
        def_config = (
            f"/etc/effective-range/{APPLICATION_NAME}/{APPLICATION_NAME}.conf.default"
        )
        args.config_file = def_config
    return {k: v for k, v in vars(args).items() if v is not None}


def _get_resource_root() -> str:
    return str(Path(os.path.dirname(__file__)).parent.absolute())


def _update_logging(arguments: dict[str, Any], configuration: dict[str, Any]) -> None:
    log_level = configuration.get("log_level", "INFO")
    log_file = configuration.get("log_file")
    if log_level != "INFO" or log_file != arguments.get("log_file"):
        setup_logging(APPLICATION_NAME, log_level, log_file, warn_on_overwrite=False)


def _init_service(
        services: list[IService],
        service: IService,
        is_required: bool,
        is_managed: bool = True,
) -> None:
    if service.is_installed():
        if is_required:
            if is_managed:
                services.append(service)
        else:
            service.set_force_stop(True)
    else:
        if is_required:
            raise ValueError(f"Mandatory {service.get_name()} service is not installed")


if __name__ == "__main__":
    main()
