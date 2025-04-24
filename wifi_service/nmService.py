# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import gi

from wifi_config import IWifiConfig, WifiNetwork

gi.require_version('NM', '1.0')

from gi.repository import NM
from gi.repository.NM import Device

from enum import Enum
from typing import Optional

from context_logger import get_logger

from wifi_dbus import IWifiDbus
from wifi_event import WifiEventType
from wifi_service import ServiceDependencies, WifiClientService, WifiClientStateEvent

log = get_logger('NetworkManagerService')


class NetworkManagerEvent(Enum):
    NM_DEVICE_STATE_UNKNOWN = WifiEventType.CLIENT_DISABLED
    NM_DEVICE_STATE_UNMANAGED = WifiEventType.CLIENT_DISABLED
    NM_DEVICE_STATE_UNAVAILABLE = WifiEventType.CLIENT_INACTIVE
    NM_DEVICE_STATE_DISCONNECTED = WifiEventType.CLIENT_DISCONNECTED
    NM_DEVICE_STATE_PREPARE = WifiEventType.CLIENT_SCANNING
    NM_DEVICE_STATE_CONFIG = WifiEventType.CLIENT_CONNECTING
    NM_DEVICE_STATE_IP_CONFIG = WifiEventType.CLIENT_CONNECTING
    NM_DEVICE_STATE_IP_CHECK = WifiEventType.CLIENT_IP_ACQUIRED
    NM_DEVICE_STATE_ACTIVATED = WifiEventType.CLIENT_CONNECTED
    NM_DEVICE_STATE_DEACTIVATING = WifiEventType.CLIENT_DISCONNECTING
    NM_DEVICE_STATE_FAILED = WifiEventType.CLIENT_FAILED

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def to_wifi_event(name: str) -> Optional['WifiEventType']:
        if name in NetworkManagerEvent.__members__:
            return NetworkManagerEvent[name].value
        else:
            return None


class NetworkManagerService(WifiClientService):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/NetworkManager_2eservice'

    def __init__(self, dependencies: ServiceDependencies, wifi_config: IWifiConfig, wifi_dbus: IWifiDbus) -> None:
        super().__init__('NetworkManager', self._SYSTEMD_DBUS_PATH, dependencies)
        self._wifi_config = wifi_config
        self._wifi_dbus = wifi_dbus
        self._interface = wifi_dbus.get_interface()

    def get_supported_events(self) -> set[WifiEventType]:
        network_manager_events = {event.value for event in NetworkManagerEvent}
        client_state_events = {event.value for event in WifiClientStateEvent}
        return network_manager_events.union(client_state_events)

    def get_interface(self) -> str:
        return self._interface

    def get_connected_ssid(self) -> Optional[str]:
        return self._wifi_dbus.get_active_ssid()

    def get_network_count(self) -> int:
        return len(self._wifi_config.get_networks())

    def get_networks(self) -> list[WifiNetwork]:
        return self._wifi_config.get_networks()

    def add_network(self, network: WifiNetwork) -> None:
        self._wifi_config.add_network(network)

    def reset_wireless(self) -> None:
        self._wifi_dbus.reset_wireless()

    def _complete_start(self) -> None:
        self._wifi_dbus.add_connection_handler(self._on_connection_changed)
        self._wifi_dbus.enable_wireless()

    def _on_service_state_changed(self, state: str) -> None:
        super()._on_service_state_changed(state)

        if event_type := NetworkManagerEvent.to_wifi_event(state):
            self._execute_callback(event_type, {})

    def _on_connection_changed(self, device: Device, new: int, old: int, reason: int) -> None:
        new_state = NM.DeviceState(new).value_name
        state_reason = NM.DeviceStateReason(reason).value_name

        log.debug(f'Connection changed: {new_state} - {state_reason}')

        if event_type := NetworkManagerEvent.to_wifi_event(str(new_state)):
            self._execute_callback(event_type, {})
