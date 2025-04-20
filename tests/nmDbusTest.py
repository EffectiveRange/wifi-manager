import unittest
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from gi.repository import GLib
from gi.repository.NM import Client, DeviceWifi, AccessPoint, Device

from wifi_config import WifiNetwork
from wifi_dbus import NetworkManagerDbus


class NmDbusTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging('wifi-manager', 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_interface(self):
        # Given
        client, device = create_components()
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        result = nm_dbus.get_interface()

        # Then
        self.assertEqual('wlan0', result)

    def test_add_connection_handler(self):
        # Given
        client, device = create_components()
        client.get_devices.side_effect = [[], [], [device]]
        nm_dbus = NetworkManagerDbus('wlan0', client, 2, 0)

        handler = MagicMock()

        # When
        nm_dbus.add_connection_handler(handler)

        # Then
        device.connect.assert_called_once_with('state-changed', handler)

    def test_add_connection_handler_when_exceeding_max_retries(self):
        # Given
        client, device = create_components()
        client.get_devices.side_effect = [[], [], [], [device]]
        nm_dbus = NetworkManagerDbus('wlan0', client, 2, 0)

        handler = MagicMock()

        # When
        nm_dbus.add_connection_handler(handler)

        # Then
        device.connect.assert_not_called()

    def test_get_active_ssid(self):
        # Given
        client, device = create_components()
        ap = MagicMock(spec=AccessPoint)
        ap.get_ssid.return_value = GLib.Bytes.new('test-ssid'.encode())
        device.get_active_access_point.return_value = ap
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        result = nm_dbus.get_active_ssid()

        # Then
        self.assertEqual('test-ssid', result)

    def test_get_active_ssid_when_no_active_connection(self):
        # Given
        client, device = create_components()
        device.get_active_access_point.return_value = None
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        result = nm_dbus.get_active_ssid()

        # Then
        self.assertIsNone(result)

    def test_add_network_and_not_activate(self):
        # Given
        client, device = create_components()
        ap = MagicMock(spec=AccessPoint)
        ap.get_ssid.return_value = GLib.Bytes.new('test-ap-3'.encode())
        device.get_access_points.return_value = [ap]
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        nm_dbus.add_network(WifiNetwork('test-ap-3', 'test-psk-3', False, 3))
        nm_dbus._on_added(client, MagicMock(), None)

        # Then
        client.add_connection_async.assert_called_once()
        device.request_scan.assert_not_called()
        client.activate_connection_async.assert_not_called()
        client.add_connection_finish.assert_called_once()
        client.activate_connection_finish.assert_not_called()

    def test_add_network_and_activate(self):
        # Given
        client, device = create_components()
        ap = MagicMock(spec=AccessPoint)
        ap.get_ssid.return_value = GLib.Bytes.new('test-ap-3'.encode())
        device.get_access_points.return_value = [ap]
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        nm_dbus.add_network(WifiNetwork('test-ap-3', 'test-psk-3', True, 3))
        nm_dbus._on_added(client, MagicMock(), None)
        nm_dbus._on_activated(client, MagicMock(), None)

        # Then
        client.add_connection_async.assert_called_once()
        device.request_scan.assert_called_once()
        client.activate_connection_async.assert_called_once()
        client.add_connection_finish.assert_called_once()
        client.activate_connection_finish.assert_called_once()

    def test_add_network_and_not_activate_when_no_such_ap(self):
        # Given
        client, device = create_components()
        nm_dbus = NetworkManagerDbus('wlan0', client)

        # When
        nm_dbus.add_network(WifiNetwork('test-ap-3', 'test-psk-3', True, 3))
        nm_dbus._on_added(client, MagicMock(), None)

        # Then
        client.add_connection_async.assert_called_once()
        client.activate_connection_async.assert_not_called()
        client.add_connection_finish.assert_called_once()
        client.activate_connection_finish.assert_not_called()


def create_components():
    loopback_device = MagicMock(spec=Device)
    loopback_device.get_iface.return_value = 'lo'
    wlan_0_device = MagicMock(spec=DeviceWifi)
    wlan_0_device.get_iface.return_value = 'wlan0'
    client = MagicMock(spec=Client)
    client.get_devices.return_value = [loopback_device, wlan_0_device]

    return client, wlan_0_device


if __name__ == '__main__':
    unittest.main()
