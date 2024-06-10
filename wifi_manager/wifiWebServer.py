# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from threading import Thread
from typing import Any, Optional

from context_logger import get_logger
from flask import Flask, render_template, request, json, redirect, Request, url_for
from waitress.server import create_server
from werkzeug import Response

from wifi_manager import IEventHandler
from wifi_utility import IPlatform

log = get_logger('WifiWebServer')


class IWebServer(object):

    def run(self) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        raise NotImplementedError()

    def is_running(self) -> bool:
        raise NotImplementedError()


class WebServerConfig(object):

    def __init__(self, hotspot_ip: str, server_port: int, resource_root: str) -> None:
        self.hotspot_ip = hotspot_ip
        self.server_port = server_port
        self.resource_root = resource_root


class WifiWebServer(IWebServer):

    def __init__(self, configuration: WebServerConfig, platform: IPlatform,
                 event_handler: IEventHandler) -> None:
        self._configuration = configuration
        self._platform = platform
        self._event_handler = event_handler
        self._app = Flask(__name__,
                          template_folder=f'{self._configuration.resource_root}/templates',
                          static_folder=f'{self._configuration.resource_root}/static')
        self._hotspot_host = f'{self._configuration.hotspot_ip}:{self._configuration.server_port}'
        self._server = create_server(self._app, listen=f'*:{self._configuration.server_port}')
        self._is_running = False
        self._network_configured = False
        self._hostname: Optional[str] = None

        self._set_up_api_endpoints()
        self._set_up_web_endpoints()
        self._set_up_captive_portal()

        @self._app.after_request
        def after_request(response: object) -> object:
            if self._network_configured:
                self._network_configured = False
                Thread(target=self._event_handler.on_add_network_completed).start()

            return response

    def __enter__(self) -> 'WifiWebServer':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()

    def run(self) -> None:
        log.info('Starting web server', port=self._configuration.server_port)
        try:
            self._hostname = self._platform.get_hostname()
            self._is_running = True
            self._server.run()
        except Exception as error:
            log.info('Shutdown', reason=error)

    def shutdown(self) -> None:
        log.info('Shutting down')
        self._platform.clean_up_ip_tables()
        self._server.close()
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running

    def _set_up_captive_portal(self) -> None:
        self._platform.clean_up_ip_tables()
        self._platform.set_up_ip_tables(self._configuration.hotspot_ip, self._hotspot_host)

        @self._app.route('/', defaults={'path': ''})
        @self._app.route('/<path:path>')
        def redirect_all(path: str) -> Response:
            target = url_for('configure_by_web')
            log.debug('Redirecting', request=request, target=target)
            return redirect(target)

    def _convert_json_configuration(self, configuration_request: Request) -> dict[str, Any]:
        try:
            configuration = json.loads(configuration_request.data)
            ssid = configuration['ssid']
            password = configuration['password']
            return {'ssid': ssid, 'password': password}
        except Exception as error:
            log.error('Invalid json configuration', error=error)
            return {}

    def _convert_form_configuration(self, configuration_request: Request) -> dict[str, Any]:
        try:
            ssid = configuration_request.form['ssid']
            password = configuration_request.form['password']
            return {'ssid': ssid, 'password': password}
        except Exception as error:
            log.error('Invalid form configuration', error=error)
            return {}

    def _set_up_api_endpoints(self) -> None:

        @self._app.route('/api/configure', methods=['POST'])
        def configure_by_api() -> tuple[str, int]:
            log.info('Configuration API request', request=request)

            configuration = self._convert_json_configuration(request)

            if configuration:
                self._network_configured = self._event_handler.on_add_network_requested(configuration)

            return ('Configured network', 200) if self._network_configured \
                else ('Failed to configure network', 400)

        @self._app.route('/api/identify', methods=['POST'])
        def identify_by_api() -> tuple[str, int]:
            log.info('Identification API request', request=request)

            signal_sent = self._event_handler.on_identify_requested()

            return ('Identification signal sent', 200) if signal_sent else \
                ('Failed to send identification signal', 400)

    def _set_up_web_endpoints(self) -> None:

        @self._app.route('/web/configure', methods=['GET', 'POST'])
        def configure_by_web() -> str:
            log.info('Configuration web request', request=request)

            if request.method == 'POST':
                ssid = ''
                password = ''
                configuration = self._convert_form_configuration(request)

                if configuration:
                    self._network_configured = self._event_handler.on_add_network_requested(configuration)
                    ssid = configuration['ssid']
                    password = configuration['password']

                result = 'Configured network' if self._network_configured else 'Failed to configure network'

                return render_template('configure.html', hostname=self._hostname, ssid=ssid, password=password,
                                       result=result)

            return render_template('configure.html', hostname=self._hostname, ssid='', password='', result='...')

        @self._app.route('/web/identify', methods=['GET', 'POST'])
        def identify_by_web() -> str:
            log.info('Identification web request', request=request)

            if request.method == 'POST':
                signal_sent = self._event_handler.on_identify_requested()

                result = 'Identification signal sent' if signal_sent else 'Failed to send identification signal'

                return render_template('identify.html', hostname=self._hostname, result=result)

            return render_template('identify.html', hostname=self._hostname, result='...')
