import unittest
from unittest import TestCase, mock
from unittest.mock import MagicMock

from context_logger import setup_logging

from wifi_event import WifiEventType
from wifi_manager import WifiManager, IWebServer, WifiControlState, IWifiControl, IEventHandler
from wifi_service import IService, ServiceError
from wifi_utility import ISsdpServer


class WifiManagerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_components_started_and_stopped(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks()

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            ssdp_server.start.assert_called_once()
            web_server.run.assert_called_once()

        ssdp_server.shutdown.assert_called_once()
        web_server.shutdown.assert_called_once()
        event_handler.shutdown.assert_called_once()

    def test_setup_services(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks()
        service1 = MagicMock(spec=IService)
        service1.get_name.return_value = 'service1'
        service2 = MagicMock(spec=IService)
        service2.get_name.return_value = 'service2'
        services = [service1, service2]

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

        # Then
        service1.setup.assert_called_once()
        service2.setup.assert_called_once()

    def test_shutting_down_when_fatal_service_error_raised(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks()
        service1 = MagicMock(spec=IService)
        service1.get_name.return_value = 'service1'
        service1.setup.side_effect = ServiceError('service1', 'Setup failed')
        service2 = MagicMock(spec=IService)
        service2.get_name.return_value = 'service2'
        services = [service1, service2]

        wifi_manager = WifiManager(services, wifi_control, event_handler, web_server, ssdp_server)

        # When
        wifi_manager.run()

        # Then
        web_server.shutdown.assert_called_once()
        ssdp_server.shutdown.assert_called_once()
        event_handler.shutdown.assert_called_once()

    def test_setup_event_handling(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks()
        service1 = MagicMock(spec=IService)
        service1.get_name.return_value = 'service1'
        service1.get_supported_events.return_value = [WifiEventType.CLIENT_CONNECTED, WifiEventType.CLIENT_DISCONNECTED]
        services.append(service1)
        service2 = MagicMock(spec=IService)
        service2.get_name.return_value = 'service2'
        service2.get_supported_events.return_value = [WifiEventType.HOTSPOT_STARTED, WifiEventType.HOTSPOT_STOPPED]
        services.append(service2)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

        # Then
        wifi_control.register_event_source.assert_has_calls([
            mock.call(WifiEventType.CLIENT_CONNECTED, service1),
            mock.call(WifiEventType.CLIENT_DISCONNECTED, service1),
            mock.call(WifiEventType.HOTSPOT_STARTED, service2),
            mock.call(WifiEventType.HOTSPOT_STOPPED, service2)], any_order=True)
        event_handler.register_event_handlers.assert_called_once()

    def test_ssdp_server_started(self):
        # Given
        wifi_status = {'ssid': 'test-network', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'}
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(wifi_status=wifi_status)
        wifi_control.get_ip_address.return_value = wifi_status['ip']
        ssdp_server = MagicMock()

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            ssdp_server.start.assert_called_with('1.2.3.4')

    def test_ssdp_server_not_started_when_hotspot_ip_is_set(self):
        # Given
        wifi_status = {'ssid': 'test-network', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'}
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(wifi_status=wifi_status)
        wifi_control.is_hotspot_ip_set.return_value = True
        ssdp_server = MagicMock()

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            ssdp_server.start.assert_not_called()

    def test_hotspot_mode_started_when_no_networks_configured(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(
            wifi_state=WifiControlState.CLIENT, wifi_status=None)
        wifi_control.get_network_count.return_value = 0

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            wifi_control.start_hotspot_mode.assert_called()

    def test_client_mode_started_when_initial_state_is_hotspot(self):
        # Given
        wifi_status = {'ssid': 'er-edge-12345678', 'ip': '192.168.100.1', 'mac': '00:11:22:33:44:55'}
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(
            wifi_state=WifiControlState.HOTSPOT, wifi_status=wifi_status)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            wifi_control.start_client_mode.assert_called()

    def test_client_mode_restarted_when_in_client_mode_and_not_connected(self):
        # Given
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks()

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            wifi_control.start_client_mode.assert_called()

    def test_client_mode_restarted_when_in_client_mode_and_no_ip_address(self):
        # Given
        wifi_status = {'ssid': 'test-network', 'ip': None, 'mac': '00:11:22:33:44:55'}
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(wifi_status=wifi_status)

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            wifi_control.start_client_mode.assert_called()

    def test_client_mode_started_when_in_client_mode_and_hotspot_ip_is_set(self):
        # Given
        wifi_status = {'ssid': 'test-network', 'ip': '192.168.100.1', 'mac': '00:11:22:33:44:55'}
        services, wifi_control, event_handler, web_server, ssdp_server = create_mocks(
            wifi_state=WifiControlState.CLIENT, wifi_status=wifi_status)
        wifi_control.is_hotspot_ip_set.return_value = True

        with WifiManager(services, wifi_control, event_handler, web_server, ssdp_server) as wifi_manager:
            # When
            wifi_manager.run()

            # Then
            wifi_control.start_client_mode.assert_called()


def create_mocks(wifi_state=WifiControlState.CLIENT, wifi_status=None):
    wifi_control = MagicMock(spec=IWifiControl)
    wifi_control.get_state.return_value = wifi_state
    wifi_control.get_status.return_value = wifi_status
    wifi_control.is_hotspot_ip_set.return_value = False
    return [], wifi_control, MagicMock(spec=IEventHandler), MagicMock(spec=IWebServer), MagicMock(spec=ISsdpServer)


if __name__ == '__main__':
    unittest.main()
