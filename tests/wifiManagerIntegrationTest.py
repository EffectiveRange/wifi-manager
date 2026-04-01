import unittest
from pathlib import Path
from threading import Thread
from typing import Any, Optional, cast
from unittest import TestCase, mock
from unittest.mock import MagicMock

from common_utility import delete_directory, IReusableTimer, copy_file
from context_logger import setup_logging
from cysystemd.reader import JournalReader
from dbus import SystemBus
from gi.repository import NM
from gi.repository.NM import DeviceWifi
from gpiozero import DigitalOutputDevice
from systemd_dbus import Systemd
from test_utility import wait_for_assertion, wait_for_condition

from tests import RESOURCE_ROOT, TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_config import NetworkManagerConfig
from wifi_connection import ConnectionAction, ConnectionMonitorConfig, ConnectionMonitor
from wifi_dbus import NetworkManagerDbus
from wifi_event import WifiEventType
from wifi_manager import WifiManager, WifiEventHandler, WifiWebServer, WebServerConfig, WifiControl, WifiControlConfig
from wifi_service import (
    DnsmasqConfig,
    HostapdConfig,
    ServiceDependencies,
    AvahiService,
    DnsmasqService,
    HostapdService,
    IService, NetworkManagerService,
)
from wifi_utility import IPlatformAccess, ServiceJournal, BlinkConfig, BlinkControl


class WifiManagerIntegrationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_application_shuts_down_when_fails_to_add_event_handler_to_network_manager(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        nm_service = get_wifi_client_service(services)
        nm_dbus = cast(NetworkManagerDbus, nm_service._wifi_dbus)
        nm_dbus._client.get_devices.return_value = [MagicMock(spec=DeviceWifi)]

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            self.assertFalse(web_server.is_running())

    def test_dnsmasq_config_reloaded_and_initialization_completed(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        dhcp_server_service = get_dhcp_server_service(services)
        dhcp_server_service._config_reloaded.clear()

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_assertion(1, systemd.restart_service.assert_called_with, 'dnsmasq')

            # When
            trigger_event(dhcp_server_service._on_property_changed, [None, {'ActiveState': 'activating'}, None])
            trigger_event(dhcp_server_service._on_property_changed, [None, {'ActiveState': 'active'}, None])

            # Then
            wait_for_initialization(web_server)

    def test_timer_cancelled_when_connected_to_a_network(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        wifi_client_service = get_wifi_client_service(services)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)

            # When
            trigger_event(wifi_client_service._on_connection_changed, [MagicMock(), 100, 90, 0])

            # Then
            timer.cancel.assert_called_once()

    def test_switched_to_hotspot_when_client_connection_timed_out(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)
            systemd.reset_mock()

            # When
            trigger_event(event_handler._on_client_connect_timeout)

            # Then
            systemd.start_service.assert_has_calls([mock.call('dnsmasq'), mock.call('hostapd')])

    def test_switched_back_to_client_when_peer_connection_timed_out(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)

            trigger_event(event_handler._on_client_connect_timeout)

            systemd.stop_service.reset_mock()
            systemd.start_service.reset_mock()

            trigger_event(wifi_hotspot_service._on_property_changed, [None, {'ActiveState': 'active'}, None])

            systemd.is_active.side_effect = lambda service: service == 'hostapd'

            # When
            trigger_event(event_handler._on_peer_connect_timeout)

            # Then
            systemd.stop_service.assert_called_once_with('hostapd')
            systemd.start_service.assert_called_once_with('NetworkManager')

    def test_timer_cancelled_when_peer_connected_to_hotspot(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)

            trigger_event(event_handler._on_client_connect_timeout)
            trigger_event(wifi_hotspot_service._on_property_changed, [None, {'ActiveState': 'active'}, None])

            # When
            peer_data = [WifiEventType.HOTSPOT_PEER_CONNECTED, '1.2.3.4', '00:11:22:33:44:55', 'test-peer']
            trigger_event(dhcp_server_service._on_dhcp_lease_changed, peer_data)

            # Then
            timer.cancel.assert_called_once()

    def test_switched_back_to_client_when_peer_disconnected_from_hotspot(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)

            trigger_event(event_handler._on_client_connect_timeout)
            trigger_event(wifi_hotspot_service._on_property_changed, [None, {'ActiveState': 'active'}, None])

            peer_data = [WifiEventType.HOTSPOT_PEER_CONNECTED, '1.2.3.4', '00:11:22:33:44:55', 'test-peer']
            trigger_event(dhcp_server_service._on_dhcp_lease_changed, peer_data)

            systemd.stop_service.reset_mock()
            systemd.start_service.reset_mock()
            systemd.is_active.side_effect = lambda service: service == 'hostapd'

            # When
            peer_data = [WifiEventType.HOTSPOT_PEER_DISCONNECTED, '1.2.3.4', '00:11:22:33:44:55', 'test-peer']
            event_thread = Thread(target=dhcp_server_service._on_dhcp_lease_changed, args=peer_data)
            event_thread.start()

            # Then
            event_thread.join()
            systemd.stop_service.assert_called_once_with('hostapd')
            systemd.start_service.assert_called_once_with('NetworkManager')

    def test_switched_back_to_client_when_new_network_configured(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, monitor, web_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, monitor, web_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)
            client = web_server._app.test_client()

            trigger_event(event_handler._on_client_connect_timeout)
            trigger_event(wifi_hotspot_service._on_property_changed, [None, {'ActiveState': 'active'}, None])

            systemd.stop_service.reset_mock()
            systemd.start_service.reset_mock()
            systemd.is_active.side_effect = lambda service: service == 'hostapd'

            peer_data = [WifiEventType.HOTSPOT_PEER_CONNECTED, '1.2.3.4', '00:11:22:33:44:55', 'test-peer']
            trigger_event(dhcp_server_service._on_dhcp_lease_changed, peer_data)

            # When
            response = client.post('/api/configure', json={'ssid': 'test-ssid', 'password': 'test-password'})

            # Then
            self.assertEqual(200, response.status_code)
            wait_for_assertion(1, systemd.stop_service.assert_called_once_with, 'hostapd')
            systemd.start_service.assert_called_once_with('NetworkManager')


def get_wifi_client_service(services: dict[str, IService]) -> NetworkManagerService:
    return cast(NetworkManagerService, services['NetworkManager'])


def get_wifi_hotspot_service(services: dict[str, IService]) -> HostapdService:
    return cast(HostapdService, services['hostapd'])


def get_dhcp_server_service(services: dict[str, IService]) -> DnsmasqService:
    return cast(DnsmasqService, services['dnsmasq'])


def wait_for_initialization(web_server: WifiWebServer) -> None:
    wait_for_condition(5, lambda server: server.is_running(), web_server)


def trigger_event(target: Any, args: Optional[list[Any]] = None) -> None:
    event_thread = Thread(target=target, args=args) if args else Thread(target=target)

    event_thread.start()
    event_thread.join()


def setup_mocks(ip_address='1.2.3.4', mac_address='00:11:22:33:44:55'):
    platform = MagicMock(spec=IPlatformAccess)
    platform.get_ip_address.return_value = ip_address
    platform.get_mac_address.return_value = mac_address
    platform.get_hostname.return_value = 'test-hostname'
    systemd = MagicMock(spec=Systemd)
    systemd.is_active.side_effect = lambda service: service == 'wpa_supplicant'
    timer = MagicMock(spec=IReusableTimer)

    return platform, systemd, timer


def setup_components(platform: IPlatformAccess, systemd: Systemd, timer: IReusableTimer):
    interface = 'wlan0'
    hotspot_ip = '192.168.100.1'
    dhcp_range = '192.168.100.2,192.168.100.254,255.255.255.0,2m'
    server_port = 0
    mac_address = '00:11:22:33:44:55'
    hostname = 'test-hostname'
    password = 'test-password'
    country = 'US'
    file_system_root = TEST_FILE_SYSTEM_ROOT
    hosts_config_file = f'{file_system_root}/etc/hosts'
    hostname_config_file = f'{file_system_root}/etc/hostname'
    dnsmasq_config_file = f'{file_system_root}/etc/dnsmasq.conf'
    hostapd_config_file = f'{file_system_root}/etc/hostapd/hostapd.conf'
    nm_config_file = f'{file_system_root}/etc/NetworkManager/NetworkManager.conf'
    network_config_dir = f'{file_system_root}/etc/NetworkManager/system-connections'

    copy_file(f'{TEST_RESOURCE_ROOT}/config/hosts', hosts_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/hostname', hostname_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/dnsmasq.conf', dnsmasq_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/hostapd.conf', hostapd_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/test-network1.nmconnection',
              f'{network_config_dir}/test-network1.nmconnection')

    system_bus = MagicMock(spec=SystemBus)
    reader = MagicMock(spec=JournalReader)
    wifi_device = MagicMock(spec=DeviceWifi)
    wifi_device.get_iface.return_value = interface
    nm_client = MagicMock(spec=NM.Client)
    nm_client.get_devices.return_value = [wifi_device]
    nm_dbus = NetworkManagerDbus(interface, nm_client, 3, 0.1)

    nm_config = NetworkManagerConfig(interface, config_file=nm_config_file, network_dir=network_config_dir)
    dnsmasq_config = DnsmasqConfig(interface, hotspot_ip, dhcp_range, server_port)
    hostapd_config = HostapdConfig(interface, mac_address, hostname, password, country, 0)
    service_dependencies = ServiceDependencies(platform, systemd, ServiceJournal(reader))

    dns_client_service = AvahiService(
        service_dependencies, hostname, hosts_config=hosts_config_file, hostname_config=hostname_config_file
    )
    dhcp_server_service = DnsmasqService(
        service_dependencies, system_bus, dnsmasq_config, RESOURCE_ROOT, config_file=dnsmasq_config_file
    )
    wifi_client_service = NetworkManagerService(service_dependencies, nm_config, nm_dbus, 0)
    wifi_hotspot_service = HostapdService(
        service_dependencies, hostapd_config, dhcp_server_service, RESOURCE_ROOT, config_file=hostapd_config_file
    )

    dns_client_service._config_reloaded.set()
    dhcp_server_service._config_reloaded.set()
    wifi_client_service._config_reloaded.set()
    wifi_hotspot_service._config_reloaded.set()

    connect_actions = ConnectionAction.create_actions(['restart-service sshd.service'], wifi_client_service,
                                                      systemd, platform)
    restore_actions = ConnectionAction.create_actions(
        ['reset-wireless', 'restart-service openvpn@*.service'], wifi_client_service, systemd, platform)
    connection_monitor_config = ConnectionMonitorConfig(Path(TEST_RESOURCE_ROOT) / 'config', 60, 5, 3,
                                                        list(connect_actions), list(restore_actions))
    connection_monitor = ConnectionMonitor(platform, systemd, MagicMock(spec=IReusableTimer), connection_monitor_config)
    control_config = WifiControlConfig(3, "reboot")
    wifi_control = WifiControl(wifi_client_service, wifi_hotspot_service, platform, control_config)
    blink_config = BlinkConfig(500, 0, 0, 1)
    blink_device = MagicMock(spec=DigitalOutputDevice)
    blink_control = BlinkControl(blink_config, blink_device)
    event_handler = WifiEventHandler(wifi_control, blink_control, timer, connection_monitor, 15, 120)
    web_server_config = WebServerConfig(hotspot_ip, server_port, RESOURCE_ROOT)
    web_server = WifiWebServer(web_server_config, platform, event_handler, [])

    services: dict[str, IService] = {
        dns_client_service.get_name(): dns_client_service,
        dhcp_server_service.get_name(): dhcp_server_service,
        wifi_client_service.get_name(): wifi_client_service,
        wifi_hotspot_service.get_name(): wifi_hotspot_service
    }

    return services, wifi_control, event_handler, connection_monitor, web_server


if __name__ == '__main__':
    unittest.main()
