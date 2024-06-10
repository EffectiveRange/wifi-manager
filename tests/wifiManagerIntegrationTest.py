import unittest
from threading import Thread
from typing import Any, Optional
from unittest import TestCase, mock
from unittest.mock import MagicMock

from context_logger import setup_logging
from cysystemd.reader import JournalReader
from dbus import SystemBus
from systemd_dbus import Systemd

from tests import wait_for_assertion, RESOURCE_ROOT, wait_for_condition, TEST_FILE_SYSTEM_ROOT, delete_directory, \
    copy_file, TEST_RESOURCE_ROOT
from wifi_event import WifiEventType
from wifi_manager import WifiManager, WifiEventHandler, WifiWebServer, WebServerConfig, WifiControl
from wifi_service import DnsmasqConfig, HostapdConfig, ServiceDependencies, AvahiService, DhcpcdService, \
    DnsmasqService, WpaService, HostapdService, IService
from wifi_utility import IReusableTimer, IPlatform, SsdpServer, ServiceJournal
from wifi_wpa import WpaConfig, WpaDbus


class WifiManagerIntegrationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_dnsmasq_config_reloaded_and_initialization_completed(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        dhcp_server_service = get_dhcp_server_service(services)
        dhcp_server_service._config_reloaded.clear()

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
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
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        wifi_client_service = get_wifi_client_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)

            # When
            trigger_event(wifi_client_service._on_wpa_properties_changed, [{'State': 'completed'}])

            # Then
            timer.cancel.assert_called_once()

    def test_ssdp_server_restarted_when_acquired_new_ip(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        dhcp_client_service = get_dhcp_client_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)
            platform.get_ip_address.return_value = '1.2.3.5'

            # When
            dhcpcd_event = {'Interface': 'wlan0', 'Reason': 'BOUND'}
            trigger_event(dhcp_client_service._on_dhcpcd_event_signalled, [dhcpcd_event])

            # Then
            self.assertEqual('1.2.3.5', ssdp_server.get_location())

    def test_switched_to_hotspot_when_client_connection_timed_out(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            Thread(target=wifi_manager.run).start()
            wait_for_initialization(web_server)
            systemd.reset_mock()

            # When
            trigger_event(event_handler._on_client_connect_timeout)

            # Then
            systemd.stop_service.assert_called_once_with('wpa_supplicant')
            systemd.start_service.assert_has_calls([
                mock.call('dnsmasq'),
                mock.call('hostapd')
            ])

    def test_switched_back_to_client_when_peer_connection_timed_out(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
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
            systemd.start_service.assert_has_calls([
                mock.call('dhcpcd'),
                mock.call('wpa_supplicant')
            ])

    def test_timer_cancelled_when_peer_connected_to_hotspot(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
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
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
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
            systemd.start_service.assert_has_calls([
                mock.call('dhcpcd'),
                mock.call('wpa_supplicant')
            ])

    def test_switched_back_to_client_when_new_network_configured(self):
        # Given
        platform, systemd, timer = setup_mocks()
        services, wifi_control, event_handler, web_server, ssdp_server = setup_components(platform, systemd, timer)
        wifi_hotspot_service = get_wifi_hotspot_service(services)
        dhcp_server_service = get_dhcp_server_service(services)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
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
            systemd.start_service.assert_has_calls([
                mock.call('dhcpcd'),
                mock.call('wpa_supplicant')
            ])


def get_wifi_client_service(services: list[IService]) -> WpaService:
    for service in services:
        if isinstance(service, WpaService):
            return service
    raise ValueError('WpaService not found')


def get_wifi_hotspot_service(services: list[IService]) -> HostapdService:
    for service in services:
        if isinstance(service, HostapdService):
            return service
    raise ValueError('HostapdService not found')


def get_dhcp_client_service(services: list[IService]) -> DhcpcdService:
    for service in services:
        if isinstance(service, DhcpcdService):
            return service
    raise ValueError('DhcpcdService not found')


def get_dhcp_server_service(services: list[IService]) -> DnsmasqService:
    for service in services:
        if isinstance(service, DnsmasqService):
            return service
    raise ValueError('DnsmasqService not found')


def wait_for_initialization(web_server: WifiWebServer) -> None:
    wait_for_condition(1, lambda server: server.is_running(), web_server)


def trigger_event(target: Any, args: Optional[list[Any]] = None) -> None:
    event_thread = None
    if args is None:
        event_thread = Thread(target=target)
    else:
        event_thread = Thread(target=target, args=args)
    event_thread.start()
    event_thread.join()


def setup_mocks(ip_address='1.2.3.4', mac_address='00:11:22:33:44:55'):
    platform = MagicMock(spec=IPlatform)
    platform.get_ip_address.return_value = ip_address
    platform.get_mac_address.return_value = mac_address
    platform.get_hostname.return_value = 'test-hostname'
    systemd = MagicMock(spec=Systemd)
    systemd.is_active.side_effect = lambda service: service == 'wpa_supplicant'
    timer = MagicMock(spec=IReusableTimer)

    return platform, systemd, timer


def setup_components(platform: IPlatform, systemd: Systemd, timer: IReusableTimer):
    interface = 'wlan0'
    hotspot_ip = '192.168.100.1'
    dhcp_range = '192.168.100.2,192.168.100.254,255.255.255.0,2m'
    server_port = 0
    mac_address = '00:11:22:33:44:55'
    hostname = 'test-hostname'
    password = 'test-password'
    file_system_root = TEST_FILE_SYSTEM_ROOT
    hosts_config_file = f'{file_system_root}/etc/hosts'
    hostname_config_file = f'{file_system_root}/etc/hostname'
    wpa_config_file = f'{file_system_root}/etc/wpa_supplicant/wpa_supplicant.conf'
    wpa_service_file = f'{file_system_root}/lib/systemd/system/wpa_supplicant.service'
    dhcpcd_config_file = f'{file_system_root}/etc/dhcpcd.conf'
    dnsmasq_config_file = f'{file_system_root}/etc/dnsmasq.conf'
    hostapd_config_file = f'{file_system_root}/etc/hostapd/hostapd.conf'

    copy_file(f'{TEST_RESOURCE_ROOT}/config/hosts', hosts_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/hostname', hostname_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/wpa_supplicant.conf', wpa_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/wpa_supplicant.service', wpa_service_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/dhcpcd.conf', dhcpcd_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/dnsmasq.conf', dnsmasq_config_file)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/hostapd.conf', hostapd_config_file)

    system_bus = MagicMock(spec=SystemBus)
    reader = MagicMock(spec=JournalReader)
    wpa_dbus = MagicMock(spec=WpaDbus)
    wpa_dbus.get_interface.return_value = interface
    wpa_dbus.get_current_network_ssid.return_value = 'test-network'

    wpa_config = WpaConfig(config_file=wpa_config_file)
    dnsmasq_config = DnsmasqConfig(interface, hotspot_ip, dhcp_range, server_port)
    hostapd_config = HostapdConfig(interface, mac_address, hostname, password)
    service_dependencies = ServiceDependencies(platform, systemd, ServiceJournal(reader))

    dns_client_service = AvahiService(service_dependencies, hostname, hosts_config=hosts_config_file,
                                      hostname_config=hostname_config_file)
    dhcp_client_service = DhcpcdService(service_dependencies, system_bus, interface, config_file=dhcpcd_config_file)
    dhcp_server_service = DnsmasqService(service_dependencies, system_bus, dnsmasq_config, RESOURCE_ROOT,
                                         config_file=dnsmasq_config_file)
    wifi_client_service = WpaService(service_dependencies, wpa_config, wpa_dbus, dhcp_client_service,
                                     service_file=wpa_service_file)
    wifi_hotspot_service = HostapdService(service_dependencies, hostapd_config, dhcp_server_service, RESOURCE_ROOT,
                                          config_file=hostapd_config_file)

    dns_client_service._config_reloaded.set()
    dhcp_client_service._config_reloaded.set()
    dhcp_server_service._config_reloaded.set()
    wifi_client_service._config_reloaded.set()
    wifi_hotspot_service._config_reloaded.set()

    wifi_control = WifiControl(wifi_client_service, wifi_hotspot_service)
    ssdp_server = SsdpServer('test-hostname', 'test', timeout=1)
    event_handler = WifiEventHandler(wifi_control, timer, 15, 120, ssdp_server)
    web_server_config = WebServerConfig(hotspot_ip, server_port, RESOURCE_ROOT)
    web_server = WifiWebServer(web_server_config, platform, event_handler)

    services: list[IService] = [
        dns_client_service, dhcp_client_service, dhcp_server_service, wifi_client_service, wifi_hotspot_service
    ]

    return services, wifi_control, event_handler, web_server, ssdp_server


if __name__ == '__main__':
    unittest.main()
