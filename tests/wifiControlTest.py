import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from parameterized import parameterized

from wifi_config import WifiNetwork
from wifi_event import WifiEventType
from wifi_manager import WifiControl, WifiControlState, WifiControlConfig
from wifi_service import WifiClientService, WifiHotspotService, IService
from wifi_utility import IPlatformAccess


class WifiControlTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_register_event_source(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        service = MagicMock(spec=IService)
        wifi_control.register_event_source(WifiEventType.CLIENT_CONNECTED, service)

        # Then
        self.assertEqual(service, wifi_control._event_sources[WifiEventType.CLIENT_CONNECTED])

    def test_register_event_source_fails_when_already_registered(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)
        wifi_control.register_event_source(WifiEventType.CLIENT_CONNECTED, MagicMock(spec=IService))

        # When
        service = MagicMock(spec=IService)
        wifi_control.register_event_source(WifiEventType.CLIENT_CONNECTED, service)

        # Then
        self.assertNotEqual(service, wifi_control._event_sources[WifiEventType.CLIENT_CONNECTED])

    def test_register_callback(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)
        service = MagicMock(spec=IService)
        wifi_control.register_event_source(WifiEventType.CLIENT_CONNECTED, service)

        # When
        event_handler = MagicMock()
        wifi_control.register_callback(WifiEventType.CLIENT_CONNECTED, event_handler.handle_event)

        # Then
        service.register_callback.assert_called_once_with(WifiEventType.CLIENT_CONNECTED, event_handler.handle_event)

    def test_register_callback_fails_when_no_source_registered_for_event_type(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)
        service = MagicMock(spec=IService)
        wifi_control.register_event_source(WifiEventType.CLIENT_CONNECTED, service)

        # When
        event_handler = MagicMock()
        wifi_control.register_callback(WifiEventType.HOTSPOT_PEER_CONNECTED, event_handler.handle_event)

        # Then
        service.register_callback.assert_not_called()

    def test_start_client_mode_when_hotspot_is_active(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        wifi_control.start_client_mode()

        # Then
        hotspot_service.stop.assert_called_once()
        client_service.start.assert_called_once()

    def test_start_client_mode_when_client_is_active(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        hotspot_service.is_active.return_value = False
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        wifi_control.start_client_mode()

        # Then
        hotspot_service.stop.assert_not_called()
        client_service.restart.assert_called_once()

    def test_start_hotspot_mode_when_hotspot_is_active(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        wifi_control.start_hotspot_mode()

        # Then
        hotspot_service.restart.assert_called_once()
        client_service.stop.assert_not_called()

    def test_start_hotspot_mode_when_client_is_active(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        hotspot_service.is_active.return_value = False
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        wifi_control.start_hotspot_mode()

        # Then
        client_service.stop.assert_called_once()
        hotspot_service.start.assert_called_once()

    def test_start_client_mode_when_switch_fails(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        client_service.start.side_effect = Exception("Failed to start client")
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        self.assertRaises(Exception, wifi_control.start_client_mode)

        # Then
        self.assertEqual(1, wifi_control._failures)

    def test_start_hotspot_mode_when_switch_fails(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        hotspot_service.is_active.return_value = False
        hotspot_service.start.side_effect = Exception("Failed to start hotspot")
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        self.assertRaises(Exception, wifi_control.start_hotspot_mode)

        # Then
        self.assertEqual(1, wifi_control._failures)

    def test_switching_modes_when_switch_fail_limit_reached(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        hotspot_service.is_active.return_value = False
        hotspot_service.start.side_effect = Exception("Failed to start hotspot")
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        self.assertRaises(Exception, wifi_control.start_hotspot_mode)
        self.assertRaises(Exception, wifi_control.start_hotspot_mode)

        # When
        wifi_control.start_hotspot_mode()

        # Then
        platform.execute_command.assert_called_once_with(config.switch_fail_command)
        self.assertEqual(0, wifi_control._failures)

    def test_switching_modes_when_switch_succeeds_after_failure(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        hotspot_service.is_active.return_value = False
        hotspot_service.start.side_effect = [Exception("Failed to start hotspot"), None]
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        self.assertRaises(Exception, wifi_control.start_hotspot_mode)

        # When
        wifi_control.start_hotspot_mode()

        # Then
        self.assertEqual(0, wifi_control._failures)

    def test_get_ip_address_when_in_client_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        client_service.get_ip_address.return_value = '1.2.3.4'
        hotspot_service.is_active.return_value = False
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_ip_address()

        # Then
        self.assertEqual('1.2.3.4', result)

    def test_get_ip_address_when_in_hotspot_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        hotspot_service.get_ip_address.return_value = '1.2.3.4'
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_ip_address()

        # Then
        self.assertEqual('1.2.3.4', result)

    def test_get_mac_address_when_in_client_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        client_service.get_mac_address.return_value = '11:22:33:44:55:66'
        hotspot_service.is_active.return_value = False
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_mac_address()

        # Then
        self.assertEqual('11:22:33:44:55:66', result)

    def test_get_mac_address_when_in_hotspot_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        hotspot_service.get_mac_address.return_value = '11:22:33:44:55:66'
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_mac_address()

        # Then
        self.assertEqual('11:22:33:44:55:66', result)

    @parameterized.expand([
        (WifiControlState.CLIENT, True, False),
        (WifiControlState.HOTSPOT, False, True),
        (WifiControlState.AMBIGUOUS, True, True),
        (WifiControlState.WIFI_OFF, False, False)
    ])
    def test_get_state(self, expected_state, client_active, hotspot_active):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = client_active
        hotspot_service.is_active.return_value = hotspot_active
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_state()

        # Then
        self.assertEqual(expected_state, result)

    def test_get_status_when_in_client_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = True
        client_service.get_connected_ssid.return_value = 'test-network'
        client_service.get_ip_address.return_value = '1.2.3.4'
        client_service.get_mac_address.return_value = '11:22:33:44:55:66'
        hotspot_service.is_active.return_value = False
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_status()

        # Then
        self.assertEqual({'ssid': 'test-network', 'ip': '1.2.3.4', 'mac': '11:22:33:44:55:66'}, result)

    def test_get_status_when_in_hotspot_state(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = False
        hotspot_service.is_active.return_value = True
        hotspot_service.get_hotspot_ssid.return_value = 'test-hostname'
        hotspot_service.get_ip_address.return_value = '1.2.3.4'
        hotspot_service.get_mac_address.return_value = '11:22:33:44:55:66'
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_status()

        # Then
        self.assertEqual({'ssid': 'test-hostname', 'ip': '1.2.3.4', 'mac': '11:22:33:44:55:66'}, result)

    @parameterized.expand([
        (True, True),
        (False, False)
    ])
    def test_get_status_when_in_invalid_state(self, client_active, hotspot_active):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.is_active.return_value = client_active
        hotspot_service.is_active.return_value = hotspot_active
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_status()

        # Then
        self.assertEqual({}, result)

    def test_get_network_count(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        client_service.get_network_count.return_value = 2
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        result = wifi_control.get_network_count()

        # Then
        self.assertEqual(2, result)

    def test_add_network(self):
        # Given
        client_service, hotspot_service, platform, config = create_components()
        wifi_control = WifiControl(client_service, hotspot_service, platform, config)

        # When
        network = WifiNetwork('test-network', 'test-password', True, 1)
        wifi_control.add_network(network)

        # Then
        client_service.add_network.assert_called_once_with(network)


def create_components():
    client = MagicMock(spec=WifiClientService)
    hotspot = MagicMock(spec=WifiHotspotService)
    platform = MagicMock(spec=IPlatformAccess)
    config = WifiControlConfig(3, "reboot")
    return client, hotspot, platform, config


if __name__ == '__main__':
    unittest.main()
