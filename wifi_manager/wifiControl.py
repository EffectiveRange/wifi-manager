# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from context_logger import get_logger

from wifi_config import WifiNetwork
from wifi_event import WifiEventType
from wifi_service import WifiClientService, WifiHotspotService, IService
from wifi_utility import IPlatformAccess

log = get_logger('WifiControl')


class WifiControlState(Enum):
    CLIENT = 'client'
    HOTSPOT = 'hotspot'
    WIFI_OFF = 'wifi_off'
    AMBIGUOUS = 'ambiguous'

    def __repr__(self) -> str:
        return self.value


@dataclass
class WifiControlConfig:
    switch_fail_limit: int
    switch_fail_command: str


class IWifiControl(object):

    def register_event_source(self, event: WifiEventType, event_source: IService) -> None:
        raise NotImplementedError()

    def register_callback(self, event: WifiEventType, callback: Any, *args: Any) -> None:
        raise NotImplementedError()

    def start_client_mode(self) -> None:
        raise NotImplementedError()

    def start_hotspot_mode(self) -> None:
        raise NotImplementedError()

    def get_ip_address(self) -> str:
        raise NotImplementedError()

    def get_mac_address(self) -> str:
        raise NotImplementedError()

    def get_state(self) -> WifiControlState:
        raise NotImplementedError()

    def get_status(self) -> dict[str, Optional[str]]:
        raise NotImplementedError()

    def get_network_count(self) -> int:
        raise NotImplementedError()

    def add_network(self, network: WifiNetwork) -> None:
        raise NotImplementedError()

    def is_hotspot_ip_set(self) -> bool:
        raise NotImplementedError()


class WifiControl(IWifiControl):

    def __init__(self, client_service: WifiClientService, hotspot_service: WifiHotspotService,
                 platform: IPlatformAccess, config: WifiControlConfig) -> None:
        self._client_service = client_service
        self._hotspot_service = hotspot_service
        self._platform = platform
        self._config = config
        self._failures = 0

        self._event_sources: dict[WifiEventType, IService] = {}

    def register_event_source(self, event_type: WifiEventType, event_source: IService) -> None:
        if event_type not in self._event_sources:
            self._event_sources[event_type] = event_source
        else:
            log.error('Event source already registered for event', event_type=event_type)

    def register_callback(self, event_type: WifiEventType, callback: Any, *args: Any) -> None:
        if event_type in self._event_sources:
            self._event_sources[event_type].register_callback(event_type, callback, *args)
        else:
            log.error('Event source not found for event', event_type=event_type)

    def start_client_mode(self) -> None:
        log.info('Starting client mode')

        try:
            if self._hotspot_service.is_active():
                self._hotspot_service.stop()
            if self._client_service.is_active():
                self._client_service.restart()
            else:
                self._client_service.start()
            self._failures = 0
        except Exception as error:
            self._handle_failure(error)

    def start_hotspot_mode(self) -> None:
        log.info('Starting hotspot mode')

        try:
            if self._client_service.is_active():
                self._client_service.stop()
            if self._hotspot_service.is_active():
                self._hotspot_service.restart()
            else:
                self._hotspot_service.start()
            self._failures = 0
        except Exception as error:
            self._handle_failure(error)

    def get_ip_address(self) -> str:
        state = self.get_state()

        if state == WifiControlState.HOTSPOT:
            return self._hotspot_service.get_ip_address()
        else:
            return self._client_service.get_ip_address()

    def get_mac_address(self) -> str:
        state = self.get_state()

        if state == WifiControlState.HOTSPOT:
            return self._hotspot_service.get_mac_address()
        else:
            return self._client_service.get_mac_address()

    def get_state(self) -> WifiControlState:
        state = WifiControlState.WIFI_OFF

        if self._client_service.is_active():
            if self._hotspot_service.is_active():
                state = WifiControlState.AMBIGUOUS
            else:
                state = WifiControlState.CLIENT
        elif self._hotspot_service.is_active():
            state = WifiControlState.HOTSPOT

        return state

    def get_status(self) -> dict[str, Optional[str]]:
        state = self.get_state()
        ssid = None

        if state == WifiControlState.CLIENT:
            ssid = self._client_service.get_connected_ssid()
        elif state == WifiControlState.HOTSPOT:
            ssid = self._hotspot_service.get_hotspot_ssid()

        status: dict[str, Optional[str]] = dict()

        if ssid:
            status['ssid'] = ssid
            status['ip'] = self.get_ip_address()
            status['mac'] = self.get_mac_address()

        return status

    def get_network_count(self) -> int:
        return self._client_service.get_network_count()

    def add_network(self, network: WifiNetwork) -> None:
        self._client_service.add_network(network)

    def is_hotspot_ip_set(self) -> bool:
        return self.get_ip_address() == self._hotspot_service.get_hotspot_ip()

    def _handle_failure(self, error: Exception) -> None:
        self._failures = self._failures + 1

        log.error('Failed to switch mode', error=error)

        if self._failures >= self._config.switch_fail_limit:
            log.error('Switching modes failure limit reached, taking action',
                      limit=self._config.switch_fail_limit, action=self._config.switch_fail_command)
            self._platform.execute_command(self._config.switch_fail_command)
            self._failures = 0
        else:
            raise error
