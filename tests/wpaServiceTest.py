import unittest
from os.path import exists
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import delete_directory, copy_file, create_file
from context_logger import setup_logging
from systemd_dbus import Systemd
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_event import WifiEventType
from wifi_service import WpaService, ServiceDependencies, IService, ServiceError
from wifi_utility import IPlatform, IJournal
from wifi_wpa import IWpaDbus, IWpaConfig


class WpaServiceTest(TestCase):
    WPA_SERVICE_FILE = f'{TEST_FILE_SYSTEM_ROOT}/lib/systemd/system/wpa_supplicant.service'
    SOURCE_WPA_SERVICE_FILE = f'{TEST_RESOURCE_ROOT}/config/wpa_supplicant.service'
    EXPECTED_WPA_SERVICE_FILE = f'{TEST_RESOURCE_ROOT}/expected/wpa_supplicant.service'
    WPA_RUN_DIR = f'{TEST_FILE_SYSTEM_ROOT}/run/wpa_supplicant'
    WPA_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/wpa_supplicant/wpa_supplicant.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)
        copy_file(self.SOURCE_WPA_SERVICE_FILE, self.WPA_SERVICE_FILE)

    def test_setup_updates_service_file_and_reloads_systemd_and_restarts_wpa_supplicant(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        wpa_service._config_reloaded.set()
        wpa_service.setup()

        # Then
        self.assertTrue(compare_files(self.EXPECTED_WPA_SERVICE_FILE, self.WPA_SERVICE_FILE))
        dependencies.systemd.reload_daemon.assert_called_once()
        dependencies.systemd.restart_service.assert_called_once_with('wpa_supplicant')

    def test_setup_raises_service_error_when_failed_to_update_service_file(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file='')

        # When
        self.assertRaises(ServiceError, wpa_service.setup)

        # Then
        dependencies.systemd.reload_daemon.assert_not_called()
        dependencies.systemd.restart_service.assert_not_called()

    def test_setup_calls_wpa_config_setup_when_needed(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_config.need_config_file_setup.side_effect = [True, False]
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        wpa_service._config_reloaded.set()
        wpa_service.setup()

        # Then
        wpa_config.setup_config_file.assert_called_once()

    def test_start_removes_run_file_and_starts_dhcp_client(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(
            dependencies,
            wpa_config,
            wpa_dbus,
            dhcp_client,
            service_file=self.WPA_SERVICE_FILE,
            run_dir=self.WPA_RUN_DIR,
        )
        create_file(f'{self.WPA_RUN_DIR}/wlan0', '')

        # When
        wpa_service.start()

        # Then
        self.assertFalse(exists(f'{self.WPA_RUN_DIR}/wlan0'))
        dhcp_client.start.assert_called_once()

    def test_restart_removes_run_file_and_starts_dhcp_client(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(
            dependencies,
            wpa_config,
            wpa_dbus,
            dhcp_client,
            service_file=self.WPA_SERVICE_FILE,
            run_dir=self.WPA_RUN_DIR,
        )
        create_file(f'{self.WPA_RUN_DIR}/wlan0', '')

        # When
        wpa_service.restart()

        # Then
        self.assertFalse(exists(f'{self.WPA_RUN_DIR}/wlan0'))
        dhcp_client.start.assert_called_once()

    def test_returns_supported_events(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        result = wpa_service.get_supported_events()

        # Then
        self.assertEqual(
            [
                WifiEventType.CLIENT_DISABLED,
                WifiEventType.CLIENT_INACTIVE,
                WifiEventType.CLIENT_SCANNING,
                WifiEventType.CLIENT_CONNECTING,
                WifiEventType.CLIENT_CONNECTED,
                WifiEventType.CLIENT_DISCONNECTED,
            ],
            result,
        )

    def test_returns_connected_ssid(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_dbus.get_current_network_ssid.return_value = 'test-network'
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        result = wpa_service.get_connected_ssid()

        # Then
        self.assertEqual('test-network', result)

    def test_returns_network_count(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_config.get_networks.return_value = {
            '"test-network1"': {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': '0', 'priority': '0'},
            'test-network2': {'ssid': 'test-network2', 'psk': 'test-password2', 'disabled': '1', 'priority': '1'},
        }
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        result = wpa_service.get_network_count()

        # Then
        self.assertEqual(2, result)

    def test_returns_networks(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_config.get_networks.return_value = {
            '"test-network1"': {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': '0', 'priority': '0'},
            'test-network2': {'ssid': 'test-network2', 'psk': 'test-password2', 'disabled': '1', 'priority': '1'},
        }
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        result = wpa_service.get_networks()

        # Then
        self.assertEqual(
            [
                {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': '0', 'priority': '0'},
                {'ssid': 'test-network2', 'psk': 'test-password2', 'disabled': '1', 'priority': '1'},
            ],
            result,
        )

    def test_adds_network(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        dependencies.systemd.is_active.return_value = True
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        # When
        wpa_service.add_network(
            {'ssid': 'test-network1', 'password': 'test-password1', 'enabled': '1', 'priority': '1'}
        )

        # Then
        wpa_dbus.add_network.assert_called_once_with(
            {'ssid': 'test-network1', 'psk': 'test-password1', 'disabled': 0, 'priority': '1'}
        )
        wpa_config.add_network.assert_called_once_with(
            {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': 0, 'priority': '1'}
        )

    def test_executed_callback_on_wpa_state_change_event(self):
        # Given
        dependencies, wpa_config, wpa_dbus, dhcp_client = create_components()
        wpa_service = WpaService(dependencies, wpa_config, wpa_dbus, dhcp_client, service_file=self.WPA_SERVICE_FILE)

        callback_mock = MagicMock()
        wpa_service.register_callback(WifiEventType.CLIENT_CONNECTED, callback_mock.handle_event)

        # When
        wpa_service._on_wpa_properties_changed({'State': 'completed'})

        # Then
        callback_mock.handle_event.assert_called_once_with(WifiEventType.CLIENT_CONNECTED, {})


def create_components():
    platform = MagicMock(spec=IPlatform)
    systemd = MagicMock(spec=Systemd)
    systemd.is_masked.return_value = False
    journal = MagicMock(spec=IJournal)
    dependencies = ServiceDependencies(platform, systemd, journal)
    wpa_config = MagicMock(spec=IWpaConfig)
    wpa_config.get_config_file.return_value = '/etc/wpa_supplicant/wpa_supplicant.conf'
    wpa_config.need_config_file_setup.return_value = False
    wpa_dbus = MagicMock(spec=IWpaDbus)
    wpa_dbus.get_interface.return_value = 'wlan0'
    dhcp_client = MagicMock(spec=IService)
    return dependencies, wpa_config, wpa_dbus, dhcp_client


if __name__ == '__main__':
    unittest.main()
