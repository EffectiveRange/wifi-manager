import unittest
from unittest import TestCase

from common_utility import delete_directory, copy_file
from context_logger import setup_logging
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_config import WifiNetwork
from wifi_config.wsConfig import WpaSupplicantConfig


class WpaSupplicantConfigTest(TestCase):
    WS_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/wpa_supplicant/wpa_supplicant.conf'
    SOURCE_WS_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/wpa_supplicant.conf'

    @staticmethod
    def get_expected_config_file(case) -> str:
        return f'{TEST_RESOURCE_ROOT}/expected/wpa_supplicant.{case}.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_get_network_returns_network_by_ssid(self):
        # Given
        ws_config = WpaSupplicantConfig('HU', self.SOURCE_WS_CONFIG_FILE)

        # When
        result = ws_config.get_network('"test-network1"')

        # Then
        self.assertEqual(WifiNetwork('"test-network1"', '"test-password1"', True, 0), result)

    def test_get_network_returns_none_when_no_match(self):
        # Given
        ws_config = WpaSupplicantConfig('HU', self.SOURCE_WS_CONFIG_FILE)

        # When
        result = ws_config.get_network('"missing-network"')

        # Then
        self.assertIsNone(result)

    def test_get_networks_returns_network_list(self):
        # Given
        ws_config = WpaSupplicantConfig('HU', self.SOURCE_WS_CONFIG_FILE)

        # When
        result = ws_config.get_networks()

        # Then
        self.assertEqual(2, len(result))
        self.assertEqual([
            WifiNetwork('"test-network1"', '"test-password1"', True, 0),
            WifiNetwork('test-network2', 'test-password2', False, 1)
        ], result)

    def test_get_networks_returns_empty_list_when_config_file_is_missing(self):
        # Given
        ws_config = WpaSupplicantConfig('HU', self.WS_CONFIG_FILE)

        # When
        result = ws_config.get_networks()

        # Then
        self.assertEqual([], result)

    def test_add_network_adds_new_network(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('HU', self.WS_CONFIG_FILE)

        # When
        ws_config.add_network(WifiNetwork('"test-network3"', '"test-password3"', True, 2))

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('added'), self.WS_CONFIG_FILE))

    def test_add_network_updates_network_when_ssid_already_present(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('GB', self.WS_CONFIG_FILE)

        # When
        ws_config.add_network(WifiNetwork('test-network1', 'new-password1', False, 0))

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('updated'), self.WS_CONFIG_FILE))

    def test_remove_network_removes_network_by_ssid(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('US', self.WS_CONFIG_FILE)

        # When
        ws_config.remove_network('test-network2')

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('removed'), self.WS_CONFIG_FILE))

    def test_returns_true_when_config_file_needs_setup(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('US', self.WS_CONFIG_FILE)

        # When
        result = ws_config.need_config_file_setup()

        # Then
        self.assertTrue(result)

    def test_returns_false_when_config_file_is_set_up(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('HU', self.WS_CONFIG_FILE)

        # When
        result = ws_config.need_config_file_setup()

        # Then
        self.assertFalse(result)

    def test_should_setup_config_file(self):
        # Given
        copy_file(self.SOURCE_WS_CONFIG_FILE, self.WS_CONFIG_FILE)
        ws_config = WpaSupplicantConfig('US', self.WS_CONFIG_FILE)

        # When
        ws_config.setup_config_file()

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('setup'), self.WS_CONFIG_FILE))


if __name__ == "__main__":
    unittest.main()
