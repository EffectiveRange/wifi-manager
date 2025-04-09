import unittest
from unittest import TestCase, mock
from unittest.mock import MagicMock

from context_logger import setup_logging

from wifi_config import WifiNetwork
from wifi_event import WifiEventType
from wifi_manager import WifiEventHandler, IReusableTimer, IWifiControl, WifiControlState


class WifiEventHandlerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_wifi_monitor_callbacks_registered(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler.register_event_handlers()

        # Then
        wifi_control.register_callback.assert_has_calls([
            mock.call(WifiEventType.CLIENT_STARTED, event_handler._on_client_started),
            mock.call(WifiEventType.CLIENT_DISABLED, event_handler._on_client_not_connected),
            mock.call(WifiEventType.CLIENT_INACTIVE, event_handler._on_client_not_connected),
            mock.call(WifiEventType.CLIENT_SCANNING, event_handler._on_client_not_connected),
            mock.call(WifiEventType.CLIENT_CONNECTED, event_handler._on_client_connected),
            mock.call(WifiEventType.CLIENT_IP_ACQUIRED, event_handler._on_client_ip_acquired),
            mock.call(WifiEventType.HOTSPOT_STARTED, event_handler._on_hotspot_started),
            mock.call(WifiEventType.HOTSPOT_PEER_CONNECTED, event_handler._on_peer_connected),
            mock.call(WifiEventType.HOTSPOT_PEER_RECONNECTED, event_handler._on_peer_connected),
            mock.call(WifiEventType.HOTSPOT_PEER_DISCONNECTED, event_handler._on_peer_disconnected)
        ], any_order=True)

    def test_timer_started_when_client_started(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_client_started(WifiEventType.CLIENT_SCANNING, None)

        # Then
        timer.start.assert_called_once_with(15, event_handler._on_client_connect_timeout)

    def test_timer_started_when_client_not_connected(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_client_not_connected(WifiEventType.CLIENT_SCANNING, None)

        # Then
        timer.start.assert_called_once_with(15, event_handler._on_client_connect_timeout)

    def test_hotspot_started_when_connecting_timed_out(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_client_connect_timeout()

        # Then
        wifi_control.start_hotspot_mode.assert_called_once()

    def test_timer_restarted_when_connecting_timed_out_and_failed_to_start_hotspot(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.start_hotspot_mode.side_effect = Exception('Failed to start hotspot')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_client_connect_timeout()

        # Then
        timer.restart.assert_called_once()

    def test_timer_stopped_when_client_connected(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.status = {'ssid': 'test-network', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'}

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_client_connected(WifiEventType.CLIENT_CONNECTED, {})

        # Then
        timer.cancel.assert_called_once()

    def test_timer_started_when_hotspot_started_and_there_are_configured_networks(self):
        # Given
        wifi_status = {'ssid': 'er-edge-12345678', 'ip': '192.168.100.1', 'mac': '00:11:22:33:44:55'}
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.get_status.return_value = wifi_status
        wifi_control.get_network_count.return_value = 3

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_hotspot_started(WifiEventType.HOTSPOT_STARTED, {})

        # Then
        timer.start.assert_called_once_with(120, event_handler._on_peer_connect_timeout)

    def test_timer_not_started_when_hotspot_started_and_no_networks_configured(self):
        # Given
        wifi_status = {'ssid': 'er-edge-12345678', 'ip': '192.168.100.1', 'mac': '00:11:22:33:44:55'}
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.get_status.return_value = wifi_status
        wifi_control.get_network_count.return_value = 0

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_hotspot_started(WifiEventType.HOTSPOT_STARTED, {})

        # Then
        timer.start.assert_not_called()

    def test_timer_stopped_when_peer_connected(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_connected(WifiEventType.HOTSPOT_PEER_CONNECTED,
                                         {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})

        # Then
        timer.cancel.assert_called_once()

    def test_client_started_when_peer_connect_timed_out(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_connect_timeout()

        # Then
        wifi_control.start_client_mode.assert_called_once()

    def test_timer_restarted_when_peer_connect_timed_out_and_failed_to_start_client(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.start_client_mode.side_effect = Exception('Failed to start client')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_connect_timeout()

        # Then
        timer.restart.assert_called_once()

    def test_client_started_when_peer_disconnected(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks(WifiControlState.HOTSPOT)

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_disconnected(WifiEventType.HOTSPOT_PEER_DISCONNECTED,
                                            {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})

        # Then
        wifi_control.start_client_mode.assert_called_once()

    def test_peer_disconnected_event_ignored_when_in_client_mode(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks(WifiControlState.CLIENT)

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_disconnected(WifiEventType.HOTSPOT_PEER_DISCONNECTED,
                                            {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})

        # Then
        wifi_control.start_client_mode.assert_not_called()

    def test_peer_disconnected_event_ignored_when_no_networks_configured(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks(WifiControlState.CLIENT)

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_disconnected(WifiEventType.HOTSPOT_PEER_DISCONNECTED,
                                            {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})

        # Then
        wifi_control.start_client_mode.assert_not_called()

    def test_timer_restarted_when_peer_disconnected_and_failed_to_start_client(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks(WifiControlState.HOTSPOT)
        wifi_control.start_client_mode.side_effect = Exception('Failed to start client')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler._on_peer_disconnected(WifiEventType.HOTSPOT_PEER_DISCONNECTED,
                                            {'name': 'test-peer', 'ip': '1.2.3.4', 'mac': '00:11:22:33:44:55'})

        # Then
        timer.restart.assert_called_once()

    def test_network_added_with_properties_enabled_and_priority(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.get_network_count.return_value = 3

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)
        network = {'ssid': 'test-network', 'password': 'test-password'}

        # When
        result = event_handler.on_add_network_requested(network)

        # Then
        self.assertTrue(result)
        wifi_control.add_network.assert_called_once_with(WifiNetwork('test-network', 'test-password', True, 3))

    def test_network_add_request_rejected_when_password_length_is_too_short(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.get_network_count.return_value = 3

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)
        network = {'ssid': 'test-network', 'password': 'short'}

        # When
        result = event_handler.on_add_network_requested(network)

        # Then
        self.assertFalse(result)
        wifi_control.add_network.assert_not_called()

    def test_network_add_request_rejected_when_failed_to_add_network(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.get_network_count.return_value = 3
        wifi_control.add_network.side_effect = Exception('Failed to add network')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)
        network = {'ssid': 'test-network', 'password': 'test-password'}

        # When
        result = event_handler.on_add_network_requested(network)

        # Then
        self.assertFalse(result)

    def test_client_started_when_adding_network_completed(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler.on_add_network_completed()

        # Then
        wifi_control.start_client_mode.assert_called_once()
        timer.cancel.assert_called_once()

    def test_timer_restarted_when_adding_network_completed_but_failed_to_start_client(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.start_client_mode.side_effect = Exception('Failed to start client')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler.on_add_network_completed()

        # Then
        timer.restart.assert_called_once()

    def test_returns_true_and_client_started_when_restart_client_requested(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        result = event_handler.on_restart_requested()

        # Then
        self.assertTrue(result)
        wifi_control.start_client_mode.assert_called_once()
        timer.cancel.assert_called_once()

    def test_returns_false_when_restart_client_requested_but_failed_to_start_client(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()
        wifi_control.start_client_mode.side_effect = Exception('Failed to start client')

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        result = event_handler.on_restart_requested()

        # Then
        self.assertFalse(result)

    def test_timer_cancelled_when_shutdown_called(self):
        # Given
        wifi_control, timer, client_timeout, peer_timeout = create_mocks()

        event_handler = WifiEventHandler(wifi_control, timer, client_timeout, peer_timeout)

        # When
        event_handler.shutdown()

        # Then
        timer.cancel.assert_called_once()


def create_mocks(wifi_state: WifiControlState = WifiControlState.CLIENT):
    client_timeout = 15
    peer_timeout = 120
    wifi_control = MagicMock(spec=IWifiControl)
    wifi_control.get_state.return_value = wifi_state
    return wifi_control, MagicMock(spec=IReusableTimer), client_timeout, peer_timeout


if __name__ == '__main__':
    unittest.main()
