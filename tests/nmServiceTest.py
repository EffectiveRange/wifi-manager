import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from systemd_dbus import Systemd

from wifi_config import IWifiConfig, WifiNetwork
from wifi_dbus import IWifiDbus
from wifi_event import WifiEventType
from wifi_service import ServiceDependencies, NetworkManagerService
from wifi_utility import IPlatformAccess, IJournal


class NetworkManagerServiceTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_returns_supported_events(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        result = network_manager_service.get_supported_events()

        # Then
        self.assertEqual(
            {
                WifiEventType.CLIENT_STARTED,
                WifiEventType.CLIENT_STOPPED,
                WifiEventType.CLIENT_DISABLED,
                WifiEventType.CLIENT_INACTIVE,
                WifiEventType.CLIENT_SCANNING,
                WifiEventType.CLIENT_CONNECTING,
                WifiEventType.CLIENT_CONNECTED,
                WifiEventType.CLIENT_DISCONNECTING,
                WifiEventType.CLIENT_DISCONNECTED,
                WifiEventType.CLIENT_IP_ACQUIRED,
                WifiEventType.CLIENT_FAILED,
            },
            result,
        )

    def test_returns_interface(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        result = network_manager_service.get_interface()

        # Then
        self.assertEqual('wlan0', result)

    def test_returns_connected_ssid(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        wifi_dbus.get_active_ssid.return_value = 'test-network'
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        result = network_manager_service.get_connected_ssid()

        # Then
        self.assertEqual('test-network', result)

    def test_returns_network_count(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        wifi_config.get_networks.return_value = [
            WifiNetwork('"test-network1"', '"test-password1"', True, 0),
            WifiNetwork('test-network2', 'test-password2', False, 1)
        ]
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        result = network_manager_service.get_network_count()

        # Then
        self.assertEqual(2, result)

    def test_returns_networks(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        networks = [
            WifiNetwork('"test-network1"', '"test-password1"', True, 0),
            WifiNetwork('test-network2', 'test-password2', False, 1)
        ]
        wifi_config.get_networks.return_value = networks
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        result = network_manager_service.get_networks()

        # Then
        self.assertEqual(networks, result)

    def test_adds_network(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        dependencies.systemd.is_active.return_value = True
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        network = WifiNetwork('test-network1', 'test-password1', True, 1)

        # When
        network_manager_service.add_network(network)

        # Then
        wifi_config.add_network.assert_called_once_with(network)

    def test_resets_wireless(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        network_manager_service.reset_wireless()

        # Then
        wifi_dbus.reset_wireless.assert_called_once_with()

    def test_executed_callback_on_connection_change_event(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        callback_mock = MagicMock()
        network_manager_service.register_callback(WifiEventType.CLIENT_CONNECTED, callback_mock.handle_event)

        # When
        network_manager_service._on_connection_changed(MagicMock(), 100, 90, 0)

        # Then
        callback_mock.handle_event.assert_called_once_with(WifiEventType.CLIENT_CONNECTED, {})

    def test_adds_connection_handler_on_service_start(self):
        # Given
        dependencies, wifi_config, wifi_dbus = create_dependencies()
        network_manager_service = NetworkManagerService(dependencies, wifi_config, wifi_dbus)

        # When
        network_manager_service.start()

        # Then
        wifi_dbus.add_connection_handler.assert_called_once_with(
            network_manager_service._on_connection_changed
        )


def create_dependencies():
    platform = MagicMock(spec=IPlatformAccess)
    systemd = MagicMock(spec=Systemd)
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    wifi_config = MagicMock(spec=IWifiConfig)
    wifi_config.need_config_file_setup.return_value = False
    wifi_dbus = MagicMock(spec=IWifiDbus)
    wifi_dbus.get_interface.return_value = 'wlan0'
    return dependencies, wifi_config, wifi_dbus


if __name__ == '__main__':
    unittest.main()
