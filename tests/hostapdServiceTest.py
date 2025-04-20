import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import delete_directory
from context_logger import setup_logging
from systemd_dbus import Systemd
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT, RESOURCE_ROOT
from wifi_event import WifiEventType
from wifi_service import HostapdService, HostapdConfig, ServiceDependencies, ServiceError, DhcpServerService
from wifi_utility import IPlatformAccess, IJournal


class HostapdServiceTest(TestCase):
    HOSTAPD_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/hostapd/hostapd.conf'
    EXPECTED_HOSTAPD_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/expected/hostapd.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_setup_unmasks_and_disables_and_stops_hostapd(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        dependencies.systemd.is_enabled.return_value = True
        dependencies.systemd.is_masked.return_value = True
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.EXPECTED_HOSTAPD_CONFIG_FILE
        )

        # When
        hostapd_service.setup()

        # Then
        dependencies.systemd.unmask_service.assert_called_once_with('hostapd')
        dependencies.systemd.reload_daemon.assert_called_once()
        dependencies.systemd.disable_service.assert_called_once_with('hostapd')
        dependencies.systemd.stop_service.assert_called_once_with('hostapd')

    def test_setup_updates_config_file_hostapd(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        hostapd_service.setup()

        # Then
        self.assertTrue(compare_files(self.EXPECTED_HOSTAPD_CONFIG_FILE, self.HOSTAPD_CONFIG_FILE))

    def test_setup_raises_service_error_when_failed_to_update_config_file(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(dependencies, config, dhcp_server, RESOURCE_ROOT, config_file='')

        # When
        self.assertRaises(ServiceError, hostapd_service.setup)

        # Then
        dependencies.systemd.restart_service.assert_not_called()

    def test_sets_up_interface_and_starts_dhcp_server(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        hostapd_service.start()

        # Then
        dependencies.platform.set_ip_address.assert_called_once_with('wlan0', '192.168.100.1')
        dhcp_server.start.assert_called_once()

    def test_sets_up_interface_and_restarts_dhcp_server(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        hostapd_service.restart()

        # Then
        dependencies.platform.set_ip_address.assert_called_once_with('wlan0', '192.168.100.1')
        dhcp_server.restart.assert_called_once()

    def test_returns_supported_events(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        result = hostapd_service.get_supported_events()

        # Then
        self.assertEqual(
            {WifiEventType.HOTSPOT_STARTED, WifiEventType.HOTSPOT_STOPPED, WifiEventType.HOTSPOT_FAILED}, result
        )

    def test_returns_hotspot_ssid(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        result = hostapd_service.get_hotspot_ssid()

        # Then
        self.assertEqual('test-hostname', result)

    def test_returns_hotspot_ip(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        # When
        result = hostapd_service.get_hotspot_ip()

        # Then
        self.assertEqual('192.168.100.1', result)

    def test_executed_callback_on_service_state_change_event(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        callback_mock = MagicMock()
        hostapd_service.register_callback(WifiEventType.HOTSPOT_STARTED, callback_mock.handle_event)

        # When
        hostapd_service._on_service_state_changed('active')

        # Then
        callback_mock.handle_event.assert_called_once_with(WifiEventType.HOTSPOT_STARTED, {})

    def test_suppressed_exception_when_executed_callback_raises(self):
        # Given
        dependencies, config, dhcp_server = create_components()
        hostapd_service = HostapdService(
            dependencies, config, dhcp_server, RESOURCE_ROOT, config_file=self.HOSTAPD_CONFIG_FILE
        )

        callback_mock = MagicMock()
        callback_mock.handle_event.__name__ = 'test_handler'
        callback_mock.handle_event.side_effect = Exception('test')
        hostapd_service.register_callback(WifiEventType.HOTSPOT_STARTED, callback_mock.handle_event)

        # When
        hostapd_service._on_service_state_changed('active')

        # Then
        callback_mock.handle_event.assert_called_once_with(WifiEventType.HOTSPOT_STARTED, {})


def create_components():
    platform = MagicMock(spec=IPlatformAccess)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    config = HostapdConfig('wlan0', '11:22:33:44:55:66', 'test-hostname', 'test-password', 'GB', 0)
    dhcp_server = MagicMock(spec=DhcpServerService)
    dhcp_server.get_static_ip.return_value = '192.168.100.1'
    return dependencies, config, dhcp_server


if __name__ == '__main__':
    unittest.main()
