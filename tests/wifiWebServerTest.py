import unittest
from threading import Thread
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from test_utility import wait_for_assertion

from tests import RESOURCE_ROOT
from wifi_manager import WifiWebServer, IEventHandler, WebServerConfig
from wifi_utility import IPlatform


class WifiWebServerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_startup_and_shutdown(self):
        # Given
        configuration = create_configuration(server_port=8080)
        platform, event_handler = create_mocks()

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            # When
            Thread(target=web_server.run).start()

            # Then
            wait_for_assertion(1, platform.clean_up_ip_tables.assert_called_once)
            wait_for_assertion(1, platform.set_up_ip_tables.assert_called_with, '192.168.100.1', '192.168.100.1:8080')

        platform.clean_up_ip_tables.assert_called()

    def test_returned_200_when_configured_network_by_api(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = True

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/api/configure', json={'ssid': 'test-ssid', 'password': 'test-password'})

            # Then
            event_handler.on_add_network_requested.assert_called_with(
                {'ssid': 'test-ssid', 'password': 'test-password'}
            )
            self.assertEqual(200, response.status_code)

    def test_returned_400_when_failed_to_configure_network_by_api(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/api/configure', json={'ssid': 'test-ssid', 'password': 'test-password'})

            # Then
            event_handler.on_add_network_requested.assert_called_with(
                {'ssid': 'test-ssid', 'password': 'test-password'}
            )
            self.assertEqual(400, response.status_code)

    def test_returned_400_when_api_called_with_invalid_request(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/api/configure', json='invalid json')

            # Then
            event_handler.on_add_network_requested.assert_not_called()
            self.assertEqual(400, response.status_code)

    def test_returned_200_when_identified_device_by_api(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_identify_requested.return_value = True

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/api/identify')

            # Then
            event_handler.on_identify_requested.assert_called()
            self.assertEqual(200, response.status_code)

    def test_returned_400_when_failed_to_identify_device_by_api(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_identify_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/api/identify')

            # Then
            event_handler.on_identify_requested.assert_called()
            self.assertEqual(400, response.status_code)

    def test_returned_network_configuration_form(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.get('/web/configure')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertIn('Configure Wi-Fi Network', response.text)

    def test_redirect_to_network_configuration_form(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.get('some/random/path')

            # Then
            self.assertEqual(302, response.status_code)
            self.assertIn('/web/configure', response.headers['Location'])

    def test_returned_device_identification_form(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.get('/web/identify')

            # Then
            self.assertEqual(200, response.status_code)
            self.assertIn('Identify device', response.text)

    def test_returned_success_when_configured_network_by_web(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = True

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/web/configure', data={'ssid': 'test-ssid', 'password': 'test-password'})

            # Then
            event_handler.on_add_network_requested.assert_called_with(
                {'ssid': 'test-ssid', 'password': 'test-password'}
            )
            self.assertIn('Configured network', response.text)

    def test_returned_failure_when_failed_to_configure_network_by_web(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/web/configure', data={'ssid': 'test-ssid', 'password': 'test-password'})

            # Then
            event_handler.on_add_network_requested.assert_called_with(
                {'ssid': 'test-ssid', 'password': 'test-password'}
            )
            self.assertIn('Failed to configure network', response.text)

    def test_returned_failure_when_web_called_with_invalid_request(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_add_network_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/web/configure', data='invalid form')

            # Then
            event_handler.on_add_network_requested.assert_not_called()
            self.assertIn('Failed to configure network', response.text)

    def test_returned_success_when_identified_device_by_web(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_identify_requested.return_value = True

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/web/identify')

            # Then
            event_handler.on_identify_requested.assert_called()
            self.assertIn('Identification signal sent', response.text)

    def test_returned_failure_when_failed_to_identify_device_by_web(self):
        # Given
        configuration = create_configuration()
        platform, event_handler = create_mocks()
        event_handler.on_identify_requested.return_value = False

        with WifiWebServer(configuration, platform, event_handler) as web_server:
            client = web_server._app.test_client()
            Thread(target=web_server.run).start()

            # When
            response = client.post('/web/identify')

            # Then
            event_handler.on_identify_requested.assert_called()
            self.assertIn('Failed to send identification signal', response.text)


def create_configuration(hotspot_ip='192.168.100.1', server_port=0):
    return WebServerConfig(hotspot_ip, server_port, RESOURCE_ROOT)


def create_mocks():
    return MagicMock(spec=IPlatform), MagicMock(spec=IEventHandler)


if __name__ == '__main__':
    unittest.main()
