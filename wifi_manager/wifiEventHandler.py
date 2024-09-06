# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from typing import Any, Optional

from common_utility import IReusableTimer
from context_logger import get_logger

from wifi_event import WifiEventType
from wifi_manager import IWifiControl, WifiControlState
from wifi_utility import ISsdpServer

log = get_logger('WifiEventHandler')


class IEventHandler(object):

    def register_event_handlers(self) -> None:
        raise NotImplementedError()

    def on_add_network_requested(self, configuration: dict[str, Any]) -> bool:
        raise NotImplementedError()

    def on_add_network_completed(self) -> None:
        raise NotImplementedError()

    def on_identify_requested(self) -> bool:
        raise NotImplementedError()


class WifiEventHandler(IEventHandler):

    def __init__(
        self,
        wifi_control: IWifiControl,
        timer: IReusableTimer,
        client_timeout: int,
        peer_timeout: int,
        ssdp_server: Optional[ISsdpServer] = None,
    ) -> None:
        self._client_timeout = client_timeout
        self._peer_timeout = peer_timeout
        self._wifi_control = wifi_control
        self._timer = timer
        self._ssdp_server = ssdp_server

    def register_event_handlers(self) -> None:
        self._wifi_control.register_callback(WifiEventType.CLIENT_DISABLED, self._on_client_not_connected)
        self._wifi_control.register_callback(WifiEventType.CLIENT_INACTIVE, self._on_client_not_connected)
        self._wifi_control.register_callback(WifiEventType.CLIENT_SCANNING, self._on_client_not_connected)
        self._wifi_control.register_callback(WifiEventType.CLIENT_CONNECTED, self._on_client_connected)
        self._wifi_control.register_callback(WifiEventType.CLIENT_IP_ACQUIRED, self._on_client_ip_acquired)

        self._wifi_control.register_callback(WifiEventType.HOTSPOT_STARTED, self._on_hotspot_started)
        self._wifi_control.register_callback(WifiEventType.HOTSPOT_PEER_CONNECTED, self._on_peer_connected)
        self._wifi_control.register_callback(WifiEventType.HOTSPOT_PEER_RECONNECTED, self._on_peer_connected)
        self._wifi_control.register_callback(WifiEventType.HOTSPOT_PEER_DISCONNECTED, self._on_peer_disconnected)

    def on_add_network_requested(self, configuration: dict[str, Any]) -> bool:
        if len(configuration.get('password', '')) < 8:
            return False

        network = configuration.copy()
        network['enabled'] = True

        try:
            priority = configuration.get('priority', self._wifi_control.get_network_count())
            network['priority'] = priority

            self._wifi_control.add_network(network)
            log.info('Added network', network=network)
            return True
        except Exception as error:
            log.error('Failed to add network', network=network, error=error)
            return False

    def on_add_network_completed(self) -> None:
        log.info('Configuration completed')
        try:
            self._wifi_control.start_client_mode()
            self._timer.cancel()
        except Exception as error:
            self._timer.restart()
            log.error('Failed to (re)start client mode', error=error)

    def on_identify_requested(self) -> bool:
        log.info('Sending identification signal (Buzzer/LED)')
        # TODO: implement
        return True

    def _on_client_connect_timeout(self) -> None:
        state = self._wifi_control.get_state()
        log.info('Waiting for connection timed out', wifi_mode=state, timeout_seconds=self._client_timeout)
        try:
            self._wifi_control.start_hotspot_mode()
        except Exception as error:
            log.error('Failed switching to hotspot mode', wifi_mode=state, error=error)
            self._timer.restart()

    def _on_peer_connect_timeout(self) -> None:
        state = self._wifi_control.get_state()
        log.info('Waiting for peers timed out', wifi_mode=state, timeout_seconds=self._peer_timeout)
        try:
            self._wifi_control.start_client_mode()
        except Exception as error:
            log.error('Failed switching to client mode', wifi_mode='hotspot', error=error)
            self._timer.restart()

    def _on_client_not_connected(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        log.info(
            'Trying to connect to a network',
            wifi_mode=state,
            wifi_event=event_type,
            timeout_seconds=self._client_timeout,
        )
        self._timer.start(self._client_timeout, self._on_client_connect_timeout)

    def _on_client_connected(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        status = self._wifi_control.get_status()
        log.info('Connected to hotspot', wifi_mode=state, wifi_event=event_type, network=status)
        self._timer.cancel()

    def _on_client_ip_acquired(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        status = self._wifi_control.get_status()
        log.info('IP address acquired', wifi_mode=state, wifi_event=event_type, network=status)
        self._refresh_ssdp()

    def _on_hotspot_started(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        status = self._wifi_control.get_status()
        log.info('Started hotspot', wifi_mode=state, wifi_event=event_type, hotspot=status)
        if self._wifi_control.get_network_count():
            self._timer.start(self._peer_timeout, self._on_peer_connect_timeout)

    def _on_peer_connected(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        log.info('Peer connected', wifi_mode=state, wifi_event=event_type, peer=data)
        self._timer.cancel()

    def _on_peer_disconnected(self, event_type: WifiEventType, data: Any) -> None:
        state = self._wifi_control.get_state()
        log.info('Peer disconnected', wifi_mode=state, wifi_event=event_type, peer=data)

        if state != WifiControlState.HOTSPOT or not self._wifi_control.get_network_count():
            return

        try:
            self._timer.cancel()
            self._wifi_control.start_client_mode()
        except Exception as error:
            log.error('Failed switching to client mode', wifi_mode='hotspot', error=error)
            self._timer.restart()

    def _refresh_ssdp(self) -> None:
        if self._ssdp_server:
            new_ip = self._wifi_control.get_ip_address()
            old_ip = self._ssdp_server.get_location()
            if new_ip and old_ip != new_ip:
                log.info('IP address changed, restarting SSDP server', old_ip=old_ip, new_ip=new_ip)
                self._ssdp_server.start(new_ip)
