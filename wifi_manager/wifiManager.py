# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from typing import Any

from context_logger import get_logger

from wifi_connection import IConnectionMonitor
from wifi_manager import IWebServer, IEventHandler, IWifiControl, WifiControlState
from wifi_service import IService, ServiceError

log = get_logger('WifiManager')


class WifiManager(object):

    def __init__(self, services: list[IService], wifi_control: IWifiControl, event_handler: IEventHandler,
                 connection_monitor: IConnectionMonitor, web_server: IWebServer) -> None:
        self._services = services
        self._wifi_control = wifi_control
        self._event_handler = event_handler
        self._connection_monitor = connection_monitor
        self._web_server = web_server

    def __enter__(self) -> 'WifiManager':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()

    def run(self) -> None:
        try:
            self._setup_services()

            self._setup_event_handling()

            self._handle_initial_status()

            self._web_server.run()
        except ServiceError as error:
            log.error('Fatal error occurred while running service', service=error.service, error=error)
            self.shutdown()

    def shutdown(self) -> None:
        self._web_server.shutdown()
        self._event_handler.shutdown()

    def _setup_services(self) -> None:
        for service in self._services:
            log.debug('Setting up service', service=service.get_name())
            service.setup()

    def _setup_event_handling(self) -> None:
        for service in self._services:
            for event_type in service.get_supported_events():
                log.debug('Registering event source', event_source=service.get_name(), event_type=event_type)
                self._wifi_control.register_event_source(event_type, service)

        self._event_handler.register_event_handlers()

    def _handle_initial_status(self) -> None:
        try:
            initial_state = self._wifi_control.get_state()
            initial_status = self._wifi_control.get_status()
            log.info('Retrieved initial status', wifi_mode=initial_state, wifi_status=initial_status)

            if not self._wifi_control.get_network_count():
                log.info('No networks configured, starting hotspot mode')
                self._wifi_control.start_hotspot_mode()
                return

            start_client = False

            if initial_state != WifiControlState.CLIENT:
                log.info('Not running in client mode, starting client mode')
                start_client = True
            else:
                if not initial_status:
                    log.info('Not connected to any network, restarting client mode')
                    start_client = True
                elif self._wifi_control.is_hotspot_ip_set():
                    log.info('Removing static IP address, restarting client mode')
                    start_client = True
                elif not initial_status['ip']:
                    log.info('No IP address acquired, restarting client mode')
                    start_client = True

            if start_client:
                self._wifi_control.start_client_mode()
            else:
                self._connection_monitor.start()
        except Exception as error:
            log.error('Error occurred while handling initial status', error=error)
