import unittest
from unittest import TestCase

from common_utility import delete_directory, copy_file
from context_logger import setup_logging
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_wpa.wpaConfig import WpaConfig


class WpaConfigTest(TestCase):
    WPA_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/wpa_supplicant/wpa_supplicant.conf'
    SOURCE_WPA_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/wpa_supplicant.conf'

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
        wpa_config = WpaConfig('HU', self.SOURCE_WPA_CONFIG_FILE)

        # When
        network = wpa_config.get_network('"test-network1"')

        # Then
        self.assertEqual(
            {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': '0', 'priority': '0'}, network
        )

    def test_get_network_returns_none_when_no_match(self):
        # Given
        wpa_config = WpaConfig('HU', self.SOURCE_WPA_CONFIG_FILE)

        # When
        network = wpa_config.get_network('"missing-network"')

        # Then
        self.assertIsNone(network)

    def test_get_networks_returns_network_dictionary(self):
        # Given
        wpa_config = WpaConfig('HU', self.SOURCE_WPA_CONFIG_FILE)

        # When
        networks = wpa_config.get_networks()

        # Then
        self.assertEqual(2, len(networks))
        self.assertEqual(
            {
                '"test-network1"': {
                    'ssid': '"test-network1"',
                    'psk': '"test-password1"',
                    'disabled': '0',
                    'priority': '0',
                },
                'test-network2': {'ssid': 'test-network2', 'psk': 'test-password2', 'disabled': '1', 'priority': '1'},
            },
            networks,
        )

    def test_get_networks_returns_empty_dictionary_when_config_file_is_missing(self):
        # Given
        wpa_config = WpaConfig('HU', self.WPA_CONFIG_FILE)

        # When
        networks = wpa_config.get_networks()

        # Then
        self.assertEqual({}, networks)

    def test_add_network_adds_new_network(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('HU', self.WPA_CONFIG_FILE)

        # When
        wpa_config.add_network({'ssid': '"test-network3"', 'psk': '"test-password3"', 'disabled': '0', 'priority': '2'})

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('added'), self.WPA_CONFIG_FILE))

    def test_add_network_updates_network_when_ssid_already_present(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('GB', self.WPA_CONFIG_FILE)

        # When
        wpa_config.add_network({'ssid': 'test-network2', 'psk': 'new-password2', 'disabled': '0', 'priority': '1'})

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('updated'), self.WPA_CONFIG_FILE))

    def test_remove_network_removes_network_by_ssid(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('US', self.WPA_CONFIG_FILE)

        # When
        wpa_config.remove_network('test-network2')

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('removed'), self.WPA_CONFIG_FILE))

    def test_save_networks_writes_config_file(self):
        # Given
        wpa_config = WpaConfig('HU', self.WPA_CONFIG_FILE)
        networks = [
            {'ssid': '"test-network1"', 'psk': '"test-password1"', 'disabled': '0', 'priority': '0'},
            {'ssid': 'test-network2', 'psk': 'test-password2', 'disabled': '1', 'priority': '1'},
        ]

        # When
        wpa_config.save_networks(networks)

        # Then
        self.assertTrue(compare_files(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE))

    def test_returns_true_when_config_file_needs_setup(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('US', self.WPA_CONFIG_FILE)

        # When
        needs_setup = wpa_config.need_config_file_setup()

        # Then
        self.assertTrue(needs_setup)

    def test_returns_false_when_config_file_is_set_up(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('HU', self.WPA_CONFIG_FILE)

        # When
        needs_setup = wpa_config.need_config_file_setup()

        # Then
        self.assertFalse(needs_setup)

    def test_should_setup_config_file(self):
        # Given
        copy_file(self.SOURCE_WPA_CONFIG_FILE, self.WPA_CONFIG_FILE)
        wpa_config = WpaConfig('US', self.WPA_CONFIG_FILE)

        # When
        wpa_config.setup_config_file()

        # Then
        self.assertTrue(compare_files(self.get_expected_config_file('setup'), self.WPA_CONFIG_FILE))


if __name__ == "__main__":
    unittest.main()
