import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from dbus import SystemBus
from systemd_dbus import Systemd

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT, delete_directory, RESOURCE_ROOT, compare_files
from wifi_event import WifiEventType
from wifi_service import DnsmasqService, DnsmasqConfig, ServiceDependencies, ServiceError
from wifi_utility import IPlatform, IJournal


class DnsmasqServiceTest(TestCase):
    DNSMASQ_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/dnsmasq.conf'
    EXPECTED_DNSMASQ_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/expected/dnsmasq.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_setup_enables_dnsmasq(self):
        # Given
        dependencies, system_bus, config = create_components()
        dependencies.systemd.is_enabled.return_value = False
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.EXPECTED_DNSMASQ_CONFIG_FILE)

        # When
        dnsmasq_service.setup()

        # Then
        dependencies.systemd.enable_service.assert_called_once_with('dnsmasq')
        dependencies.systemd.start_service.assert_called_once_with('dnsmasq')

    def test_setup_updates_config_file_and_restarts_dnsmasq(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        # When
        dnsmasq_service._config_reloaded.set()
        dnsmasq_service.setup()

        # Then
        self.assertTrue(compare_files(self.EXPECTED_DNSMASQ_CONFIG_FILE, self.DNSMASQ_CONFIG_FILE))
        dependencies.systemd.restart_service.assert_called_once_with('dnsmasq')

    def test_setup_raises_service_error_when_failed_to_update_config_file(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT, config_file=None)

        # When
        self.assertRaises(ServiceError, dnsmasq_service.setup)

        # Then
        dependencies.systemd.restart_service.assert_not_called()

    def test_start_sets_up_interface(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        # When
        dnsmasq_service.start()

        # Then
        dependencies.platform.execute_command.assert_called_once_with(
            'ifconfig wlan0 192.168.100.1 netmask 255.255.255.0')
        dependencies.systemd.start_service.assert_called_once_with('dnsmasq')

    def test_restart_sets_up_interface(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        # When
        dnsmasq_service.restart()

        # Then
        dependencies.platform.execute_command.assert_called_once_with(
            'ifconfig wlan0 192.168.100.1 netmask 255.255.255.0')
        dependencies.systemd.restart_service.assert_called_once_with('dnsmasq')

    def test_returns_supported_events(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        # When
        result = dnsmasq_service.get_supported_events()

        # Then
        self.assertEqual([
            WifiEventType.HOTSPOT_PEER_CONNECTED,
            WifiEventType.HOTSPOT_PEER_RECONNECTED,
            WifiEventType.HOTSPOT_PEER_DISCONNECTED], result)

    def test_returns_static_ip(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        # When
        result = dnsmasq_service.get_static_ip()

        # Then
        self.assertEqual('192.168.100.1', result)

    def test_executed_callback_on_dnsmasq_lease_change(self):
        # Given
        dependencies, system_bus, config = create_components()
        dnsmasq_service = DnsmasqService(dependencies, system_bus, config, RESOURCE_ROOT,
                                         config_file=self.DNSMASQ_CONFIG_FILE)

        callback_mock = MagicMock()
        dnsmasq_service.register_callback(WifiEventType.HOTSPOT_PEER_CONNECTED, callback_mock.handle_event)

        # When
        dnsmasq_service._on_dhcp_lease_changed(
            WifiEventType.HOTSPOT_PEER_CONNECTED, '1.2.3.4', '00:11:22:33:44:55', 'test-peer')

        # Then
        callback_mock.handle_event.assert_called_once_with(
            WifiEventType.HOTSPOT_PEER_CONNECTED, {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})


def create_components():
    platform = MagicMock(spec=IPlatform)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    system_bus = MagicMock(spec=SystemBus)
    config = DnsmasqConfig('wlan0', '192.168.100.1', '192.168.100.2,192.168.100.254,255.255.255.0,2m', 8080)
    return dependencies, system_bus, config


if __name__ == '__main__':
    unittest.main()
