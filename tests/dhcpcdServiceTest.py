import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import delete_directory, copy_file
from context_logger import setup_logging
from dbus import SystemBus
from systemd_dbus import Systemd
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_event import WifiEventType
from wifi_service import DhcpcdService, ServiceDependencies, ServiceError
from wifi_utility import IPlatformAccess, IJournal


class DhcpcdServiceTest(TestCase):
    DHCPCD_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/dhcpcd.conf'
    SOURCE_DHCPCD_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/dhcpcd.conf'
    EXPECTED_DHCPCD_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/expected/dhcpcd.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)
        copy_file(self.SOURCE_DHCPCD_CONFIG_FILE, self.DHCPCD_CONFIG_FILE)

    def test_setup_updates_config_file_and_restarts_dhcpcd(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', self.DHCPCD_CONFIG_FILE)

        # When
        dhcpcd_service._config_reloaded.set()
        dhcpcd_service.setup()

        # Then
        self.assertTrue(compare_files(self.EXPECTED_DHCPCD_CONFIG_FILE, self.DHCPCD_CONFIG_FILE))
        dependencies.systemd.restart_service.assert_called_once_with('dhcpcd')

    def test_setup_raises_service_error_when_failed_to_update_config_file(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', '')

        # When
        self.assertRaises(ServiceError, dhcpcd_service.setup)

        # Then
        dependencies.systemd.restart_service.assert_not_called()

    def test_start_resets_interface(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', self.DHCPCD_CONFIG_FILE)

        # When
        dhcpcd_service.start()

        # Then
        dependencies.platform.execute_command.assert_called_once_with('ifconfig wlan0 0.0.0.0')
        dependencies.systemd.start_service.assert_called_once_with('dhcpcd')

    def test_restart_resets_interface(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', self.DHCPCD_CONFIG_FILE)

        # When
        dhcpcd_service.restart()

        # Then
        dependencies.platform.execute_command.assert_called_once_with('ifconfig wlan0 0.0.0.0')
        dependencies.systemd.restart_service.assert_called_once_with('dhcpcd')

    def test_returns_supported_events(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', self.DHCPCD_CONFIG_FILE)

        # When
        result = dhcpcd_service.get_supported_events()

        # Then
        self.assertEqual([WifiEventType.CLIENT_IP_ACQUIRED], result)

    def test_executed_callback_on_dhcpcd_interface_bound_event(self):
        # Given
        dependencies, system_bus = create_components()
        dhcpcd_service = DhcpcdService(dependencies, system_bus, 'wlan0', self.DHCPCD_CONFIG_FILE)

        callback_mock = MagicMock()
        dhcpcd_service.register_callback(WifiEventType.CLIENT_IP_ACQUIRED, callback_mock.handle_event)

        # When
        dhcpcd_service._on_dhcpcd_event_signalled({'Interface': 'wlan0', 'Reason': 'BOUND'})

        # Then
        callback_mock.handle_event.assert_called_once_with(WifiEventType.CLIENT_IP_ACQUIRED, {})


def create_components():
    platform = MagicMock(spec=IPlatformAccess)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    system_bus = MagicMock(spec=SystemBus)
    return dependencies, system_bus


if __name__ == '__main__':
    unittest.main()
