import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from common_utility import delete_directory, copy_file
from context_logger import setup_logging
from test_utility import compare_files

from tests import TEST_FILE_SYSTEM_ROOT, TEST_RESOURCE_ROOT
from wifi_utility import PlatformConfig, IPlatformAccess


class PlatformConfigTest(TestCase):
    BOOT_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/boot/config.txt'
    DRIVER_CONFIG_FILE = f'{TEST_FILE_SYSTEM_ROOT}/etc/modprobe.d/brcmfmac.conf'
    SOURCE_BOOT_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/config.txt'
    SOURCE_DRIVER_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/config/brcmfmac.conf'
    EXPECTED_BOOT_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/expected/config.txt'
    EXPECTED_DRIVER_CONFIG_FILE = f'{TEST_RESOURCE_ROOT}/expected/brcmfmac.conf'

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_setup_when_bluetooth_disabled(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=False, disable_roaming=False)

        # Then
        self.assertFalse(result)
        self.assertTrue(compare_files(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE))

    def test_setup_when_bluetooth_not_disabled(self):
        # Given
        copy_file(self.SOURCE_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=False, disable_roaming=False)

        # Then
        self.assertTrue(result)
        self.assertTrue(compare_files(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE))

    def test_setup_when_power_save_needs_to_be_enabled(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=False, disable_roaming=False)

        # Then
        self.assertFalse(result)
        platform.set_wlan_power_save.assert_called_once_with("wlan0", True)

    def test_setup_when_power_save_needs_to_be_disabled(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=True, disable_roaming=False)

        # Then
        self.assertFalse(result)
        platform.set_wlan_power_save.assert_called_once_with("wlan0", False)

    def test_setup_when_roaming_needs_to_be_enabled(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)
        copy_file(self.EXPECTED_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=False, disable_roaming=False)

        # Then
        self.assertTrue(result)
        self.assertTrue(compare_files(self.SOURCE_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE))

    def test_setup_when_roaming_needs_to_be_disabled(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)
        copy_file(self.SOURCE_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=True, disable_roaming=True)

        # Then
        self.assertTrue(result)
        self.assertTrue(compare_files(self.EXPECTED_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE))

    def test_setup_ignores_config_files_when_already_set_up(self):
        # Given
        copy_file(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)
        copy_file(self.EXPECTED_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=True, disable_roaming=True)

        # Then
        self.assertFalse(result)
        self.assertTrue(compare_files(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE))
        self.assertTrue(compare_files(self.EXPECTED_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE))

    def test_setup_updates_config_files_when_exists(self):
        # Given
        copy_file(self.SOURCE_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE)
        copy_file(self.SOURCE_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=True, disable_roaming=True)

        # Then
        self.assertTrue(result)
        self.assertTrue(compare_files(self.EXPECTED_BOOT_CONFIG_FILE, self.BOOT_CONFIG_FILE))
        self.assertTrue(compare_files(self.EXPECTED_DRIVER_CONFIG_FILE, self.DRIVER_CONFIG_FILE))

    def test_setup_creates_config_file_when_not_exists(self):
        # Given
        platform = MagicMock(spec=IPlatformAccess)
        platform_config = PlatformConfig(platform, "wlan0", self.BOOT_CONFIG_FILE, self.DRIVER_CONFIG_FILE)

        # When
        result = platform_config.setup(disable_power_save=True, disable_roaming=True)

        # Then
        self.assertTrue(result)
        self.assertTrue(open(self.BOOT_CONFIG_FILE).readlines()[-1] == 'dtoverlay=disable-bt')
        self.assertTrue(open(self.DRIVER_CONFIG_FILE).readlines()[-1] == 'options brcmfmac roamoff=1')


if __name__ == '__main__':
    unittest.main()
