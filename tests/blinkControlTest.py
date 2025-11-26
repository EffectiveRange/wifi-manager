import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from gpiozero import DigitalOutputDevice

from wifi_utility import BlinkConfig, BlinkControl


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
        self.assertEqual(10, blink_device.on.call_count)
        self.assertEqual(10, blink_device.off.call_count)

    def test_blink_multiple_times(self):
        # Given
        blink_config, blink_device = create_components()
        blink_config.interval = 0.1
        blink_config.count = 5
        blink_control = BlinkControl(blink_config, blink_device)

        # When
        blink_control.blink()

        # Then
        self.assertEqual(25, blink_device.on.call_count)
        self.assertEqual(25, blink_device.off.call_count)


def create_components():
    blink_config = BlinkConfig(100, 0.1, 0, 1)
    blink_device = MagicMock(spec=DigitalOutputDevice)
    return blink_config, blink_device


if __name__ == '__main__':
    unittest.main()
