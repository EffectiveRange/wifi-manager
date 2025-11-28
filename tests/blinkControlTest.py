import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging

from wifi_utility import BlinkConfig, BlinkControl, BlinkDevice


class BlinkControlTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_blink_once(self):
        # Given
        blink_config, blink_device = create_components()
        blink_config.interval = 0.2
        blink_config.count = 1
        blink_control = BlinkControl(blink_config, blink_device)

        # When
        blink_control.blink()

        # Then
        blink_device.open.assert_called_once()
        self.assertEqual(10, blink_device.on.call_count)
        self.assertEqual(10, blink_device.off.call_count)
        blink_device.close.assert_called_once()

    def test_blink_multiple_times(self):
        # Given
        blink_config, blink_device = create_components()
        blink_config.interval = 0.1
        blink_config.count = 5
        blink_control = BlinkControl(blink_config, blink_device)

        # When
        blink_control.blink()

        # Then
        blink_device.open.assert_called_once()
        self.assertEqual(25, blink_device.on.call_count)
        self.assertEqual(25, blink_device.off.call_count)
        blink_device.close.assert_called_once()

    def test_closes_device_on_device_error(self):
        # Given
        blink_config, blink_device = create_components()
        blink_device.open.side_effect = Exception("Device error")
        blink_control = BlinkControl(blink_config, blink_device)

        # When
        blink_control.blink()

        # Then
        blink_device.open.assert_called_once()
        blink_device.on.assert_not_called()
        blink_device.off.assert_not_called()
        blink_device.close.assert_called_once()


def create_components():
    blink_config = BlinkConfig(100, 0.1, 0, 1)
    blink_device = MagicMock(spec=BlinkDevice)
    return blink_config, blink_device


if __name__ == '__main__':
    unittest.main()
