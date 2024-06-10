import unittest
from unittest import TestCase

from context_logger import setup_logging
from ssdpy import SSDPClient

from wifi_utility import SsdpServer


class SsdpServerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_startup_and_shutdown(self):
        # Given
        with SsdpServer('test-host', 'test-role', 1) as ssdp_server:
            # When
            ssdp_server.start('1.2.3.4')

            # Then
            self.assertIsNotNone(ssdp_server._server)
            self.assertFalse(ssdp_server._server.stopped)
            self.assertEqual('1.2.3.4', ssdp_server.get_location())

        self.assertTrue(ssdp_server._server.stopped)

    def test_not_started_when_location_is_invalid(self):
        # Given
        with SsdpServer('test-host', 'test-role', 1) as ssdp_server:
            # When
            ssdp_server.start('')

            # Then
            self.assertIsNone(ssdp_server._server)

    def test_responds_to_discovery_request(self):
        # Given
        with SsdpServer('test-host', 'test-role', 1) as ssdp_server:
            ssdp_server.start('1.2.3.4')

            # When
            devices = SSDPClient().m_search('test-role', 1)

        # Then
        self.assertTrue(len(devices) > 0)
        device = devices[0]
        self.assertEqual(device['usn'], 'test-host')
        self.assertEqual(device['nt'], 'test-role')
        self.assertEqual(device['location'], '1.2.3.4')


if __name__ == '__main__':
    unittest.main()
