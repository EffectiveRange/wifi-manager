import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging

from wifi_utility import IPlatform, WlanInterfaceSelector


class InterfaceSelectorTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_specified_interface_selected(self):
        # Given
        platform = MagicMock(spec=IPlatform)
        platform.get_wlan_interfaces.return_value = ['wlan0']
        interface_selector = WlanInterfaceSelector(platform)

        # When
        interface = interface_selector.select('wlan0')

        # Then
        self.assertEqual('wlan0', interface)
        platform.enable_wlan_interfaces.assert_called_once()

    def test_specified_interface_selected_when_multiple_available(self):
        # Given
        platform = MagicMock(spec=IPlatform)
        platform.get_wlan_interfaces.return_value = ['wlan0', 'wlan1']
        interface_selector = WlanInterfaceSelector(platform)

        # When
        interface = interface_selector.select('wlan1')

        # Then
        self.assertEqual('wlan1', interface)

    def test_first_interface_selected_when_specified_is_not_available(self):
        # Given
        platform = MagicMock(spec=IPlatform)
        platform.get_wlan_interfaces.return_value = ['wlan1']
        interface_selector = WlanInterfaceSelector(platform)

        # When
        interface = interface_selector.select('wlan0')

        # Then
        self.assertEqual('wlan1', interface)

    def test_error_raised_when_no_interface_available(self):
        # Given
        platform = MagicMock(spec=IPlatform)
        platform.get_wlan_interfaces.return_value = []
        interface_selector = WlanInterfaceSelector(platform)

        # When, Then
        self.assertRaises(ValueError, interface_selector.select, 'wlan0')


if __name__ == '__main__':
    unittest.main()
