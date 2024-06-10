import unittest
from unittest import TestCase

from context_logger import setup_logging

from tests import TEST_RESOURCE_ROOT, TEST_FILE_SYSTEM_ROOT, delete_directory
from wifi_utility import ConfigLoader


class ConfigLoaderTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_configuration_loaded_when_file_exists(self):
        # Given
        config_file = f'{TEST_RESOURCE_ROOT}/config/wifi-manager.conf'
        arguments = {'config_file': config_file}
        configuration_loader = ConfigLoader(TEST_RESOURCE_ROOT)

        # When
        configuration = configuration_loader.load(arguments)

        # Then
        self.assertEqual('test_value', configuration['test_key'])
        self.assertEqual(config_file, configuration['config_file'])

    def test_configuration_loaded_when_file_not_exists(self):
        # Given
        arguments = {'config_file': f'{TEST_FILE_SYSTEM_ROOT}/etc/wifi-manager.conf'}
        configuration_loader = ConfigLoader(TEST_RESOURCE_ROOT)

        # When
        configuration = configuration_loader.load(arguments)

        # Then
        self.assertEqual('test_value', configuration['test_key'])

    def test_configuration_loaded_and_value_updated_from_argument(self):
        # Given
        arguments = {'config_file': f'{TEST_RESOURCE_ROOT}/config/wifi-manager.conf', 'test_key': 'new_value'}
        configuration_loader = ConfigLoader(TEST_RESOURCE_ROOT)

        # When
        configuration = configuration_loader.load(arguments)

        # Then
        self.assertEqual('new_value', configuration['test_key'])


if __name__ == '__main__':
    unittest.main()
