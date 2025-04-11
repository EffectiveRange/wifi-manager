# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import time

import gi

from wifi_config import WifiNetwork

gi.require_version('NM', '1.0')

from typing import Any, Optional

from context_logger import get_logger

from gi.repository import NM
from gi.repository.Gio import AsyncResult
from gi.repository.NM import DeviceWifi, Client, Connection

from wifi_dbus import IWifiDbus, bytes_to_str, str_to_bytes

log = get_logger('NetworkManagerDbus')


class NetworkManagerDbus(IWifiDbus):

    def __init__(self, interface: str, client: Client) -> None:
        self._interface = interface
        self._client = client

    def get_interface(self) -> str:
        return self._interface

    def add_connection_handler(self, on_connection_changed: Any) -> None:
        handler_added = False

        while not handler_added:
            if device := self._get_device():
                device.connect('state-changed', on_connection_changed)
                handler_added = True
                log.info('Added connection handler', interface=self._interface)
            else:
                log.warning('Failed to add connection handler, retrying...', interface=self._interface)
                time.sleep(1)

    def get_active_ssid(self) -> Optional[str]:
        if device := self._get_device():
            if ap := device.get_active_access_point():
                return bytes_to_str(ap.get_ssid())

        return None

    def add_network(self, network: WifiNetwork) -> None:
        ssid_bytes = str_to_bytes(network.ssid)

        setting_connection = NM.SettingConnection.new()
        setting_connection.set_property(NM.SETTING_CONNECTION_ID, network.ssid)
        setting_connection.set_property(NM.SETTING_CONNECTION_INTERFACE_NAME, self._interface)
        setting_connection.set_property(NM.SETTING_CONNECTION_TYPE, NM.SETTING_WIRELESS_SETTING_NAME)
        setting_connection.set_property(NM.SETTING_CONNECTION_AUTOCONNECT_PRIORITY, network.priority)

        setting_wireless = NM.SettingWireless.new()
        setting_wireless.set_property(NM.SETTING_WIRELESS_SSID, ssid_bytes)

        setting_security = NM.SettingWirelessSecurity.new()
        setting_security.set_property(NM.SETTING_WIRELESS_SECURITY_KEY_MGMT, 'wpa-psk')
        setting_security.set_property(NM.SETTING_WIRELESS_SECURITY_PSK, network.password)

        connection = NM.SimpleConnection.new()
        connection.add_setting(setting_connection)
        connection.add_setting(setting_wireless)
        connection.add_setting(setting_security)

        self._client.add_connection_async(connection, True, None, self._on_added, None)

        if network.enabled:
            self._activate_network(network.ssid, connection)

    def _activate_network(self, ssid: str, connection: Connection) -> None:
        if device := self._get_device():
            device.request_scan()

            if ap := next((ap for ap in device.get_access_points() if bytes_to_str(ap.get_ssid()) == ssid), None):
                self._client.activate_connection_async(
                    connection, device, ap.get_path(), None, self._on_activated, None)

    def _get_device(self) -> Optional[DeviceWifi]:
        return next((dev for dev in self._client.get_devices() if
                     dev.get_iface() == self._interface and isinstance(dev, DeviceWifi)), None)

    def _on_added(self, client: Client, result: AsyncResult, data: Any) -> None:
        client.add_connection_finish(result)

    def _on_activated(self, client: Client, result: AsyncResult, data: Any) -> None:
        client.activate_connection_finish(result)
