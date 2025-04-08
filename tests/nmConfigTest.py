import os.path
import unittest
from unittest import TestCase

from common_utility import delete_directory, copy_file, create_directory
from context_logger import setup_logging
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_config import NetworkManagerConfig, WifiNetwork


class NetworkManagerConfigTest(TestCase):
    NM_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/NetworkManager/NetworkManager.conf'
    NM_NETWORK_DIR = f'{TEST_FILE_SYSTEM_ROOT}/etc/NetworkManager/system-connections'
    SOURCE_NM_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/NetworkManager.conf'

    @staticmethod
    def get_expected_config_file(ssid) -> str:
        return f'{TEST_RESOURCE_ROOT}/expected/{ssid}.nmconnection'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)
        create_config_files()

    def test_get_config_file(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        result = nm_config.get_config_file()

        # Then
        self.assertEqual(self.NM_CONFIG_FILE, result)

    def test_get_network_returns_network_by_ssid(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        result = nm_config.get_network('test-network1')

        # Then
        self.assertEqual(WifiNetwork('test-network1', 'test-password1', True, 0), result)

    def test_get_network_returns_none_when_no_match(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        result = nm_config.get_network('"missing-network"')

        # Then
        self.assertIsNone(result)

    def test_get_networks_returns_network_list(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        result = nm_config.get_networks()

        # Then
        self.assertEqual(2, len(result))
        self.assertIn(WifiNetwork('test-network1', 'test-password1', True, 0), result)
        self.assertIn(WifiNetwork('test-network2', 'test-password2', False, 1), result)

    def test_get_networks_returns_empty_list_when_config_file_is_missing(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, TEST_FILE_SYSTEM_ROOT)

        # When
        result = nm_config.get_networks()

        # Then
        self.assertEqual([], result)

    def test_add_network_adds_new_network(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        nm_config.add_network(WifiNetwork('test-network3', 'test-password3%', True, 2))

        # Then
        self.assertTrue(compare_files(
            self.get_expected_config_file('test-network3'),
            f'{self.NM_NETWORK_DIR}/test-network3.nmconnection', ['uuid = ']))

    def test_add_network_updates_network_when_ssid_already_present(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        nm_config.add_network(WifiNetwork('test-network1', 'new-password1', False, 3))

        # Then
        self.assertTrue(compare_files(
            self.get_expected_config_file('test-network1'),
            f'{self.NM_NETWORK_DIR}/test-network1.nmconnection', ['uuid = ']))

    def test_remove_network_removes_network_by_ssid(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        nm_config.remove_network('test-network2')

        # Then
        self.assertFalse(os.path.exists(f'{self.NM_NETWORK_DIR}/test-network2.nmconnection'))

    def test_returns_false(self):
        # Given
        nm_config = NetworkManagerConfig('wlan0', self.NM_CONFIG_FILE, self.NM_NETWORK_DIR)

        # When
        result = nm_config.need_config_file_setup()

        # Then
        self.assertFalse(result)


def create_config_files():
    create_directory(NetworkManagerConfigTest.NM_NETWORK_DIR)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/test-network1.nmconnection', NetworkManagerConfigTest.NM_NETWORK_DIR)
    copy_file(f'{TEST_RESOURCE_ROOT}/config/test-network2.nmconnection', NetworkManagerConfigTest.NM_NETWORK_DIR)


if __name__ == "__main__":
    unittest.main()
