# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from subprocess import CalledProcessError
from threading import Thread
from typing import Any, Optional

from context_logger import get_logger
from flask import Flask, render_template, request, json, redirect, Request, url_for
from waitress.server import create_server
from werkzeug import Response

from wifi_manager import IEventHandler
from wifi_utility import IPlatformAccess

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

    def __init__(self, configuration: WebServerConfig, platform: IPlatformAccess, event_handler: IEventHandler,
                 command_definitions: list[str]) -> None:
        self._configuration = configuration
        self._platform = platform
        self._event_handler = event_handler
        self._app = Flask(
            __name__,
            template_folder=f'{self._configuration.resource_root}/templates',
            static_folder=f'{self._configuration.resource_root}/static',
        )
        self._hotspot_host = f'{self._configuration.hotspot_ip}:{self._configuration.server_port}'
        self._server = create_server(self._app, listen=f'*:{self._configuration.server_port}')
        self._is_running = False
        self._network_configured = False
        self._hostname: Optional[str] = None

        self._set_up_api_endpoints()
        self._set_up_configuration_web_endpoints()
        self._set_up_operation_web_endpoints()
        self._set_up_execution_web_endpoints()
        self._set_up_captive_portal()

        self._commands = self._get_commands(command_definitions)

        @self._app.after_request
        def after_request(response: object) -> object:
            if self._network_configured:
                self._network_configured = False
                Thread(target=self._event_handler.on_add_network_completed).start()

            return response

    def _get_commands(self, command_definitions: list[str]) -> list[dict[str, str]]:
        commands = []

        for definition in command_definitions:
            if ':' in definition.strip():
                name, value = definition.split(':', 1)
                commands.append({
                    'name': name.strip(),
                    'value': value.strip()
                })

        return commands

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
            self._is_running = False
            log.info('Server exited', reason=error)

    def shutdown(self) -> None:
        log.info('Shutting down')
        try:
            self._platform.clean_up_ip_tables()
            self._server.close()
        except Exception as error:
            log.info('Shutdown', reason=error)
        finally:
            self._is_running = False

    def is_running(self) -> bool:
        return self._is_running

    def _set_up_captive_portal(self) -> None:
        self._platform.clean_up_ip_tables()
        self._platform.set_up_ip_tables(self._configuration.hotspot_ip, self._hotspot_host)

        @self._app.route('/', defaults={'path': ''})
        @self._app.route('/<path:path>')
        def redirect_all(path: str) -> Response:
            target = url_for('get_configuration_page')
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

            return ('Configured network', 200) if self._network_configured else ('Failed to configure network', 400)

        @self._app.route('/api/restart', methods=['POST'])
        def restart_by_api() -> tuple[str, int]:
            log.info('Restart API request', request=request)

            restart_requested = self._event_handler.on_restart_requested()

            return ('Restarted client mode', 200) if restart_requested else ('Failed to restart client mode', 400)

        @self._app.route('/api/identify', methods=['POST'])
        def identify_by_api() -> tuple[str, int]:
            log.info('Identification API request', request=request)

            signal_sent = self._event_handler.on_identify_requested()

            return ('Identification signal sent', 200) if signal_sent else ('Failed to send identification signal', 400)

    def _set_up_configuration_web_endpoints(self) -> None:

        @self._app.route('/web/configuration', methods=['GET'])
        def get_configuration_page() -> str:
            log.info('Configuration page', request=request)

            return render_template(
                'configuration.html',
                hostname=self._hostname,
                ssid='',
                password='',
                configure_result='...'
            )

        @self._app.route('/web/configure', methods=['POST'])
        def configure_by_web() -> str:
            log.info('Configuration web request', request=request)

            ssid = ''
            password = ''
            configuration = self._convert_form_configuration(request)

            if configuration:
                self._network_configured = self._event_handler.on_add_network_requested(configuration)
                ssid = configuration['ssid']
                password = configuration['password']

            result = 'Configured network' if self._network_configured else 'Failed to configure network'

            return render_template(
                'configuration.html',
                hostname=self._hostname,
                ssid=ssid,
                password=password,
                configure_result=result
            )

    def _set_up_operation_web_endpoints(self) -> None:

        @self._app.route('/web/operation', methods=['GET'])
        def get_operation_page() -> str:
            log.info('Operation page', request=request)

            return render_template(
                'operation.html',
                hostname=self._hostname,
                identify_result='...',
                restart_result='...'
            )

        @self._app.route('/web/identify', methods=['POST'])
        def identify_by_web() -> str:
            log.info('Identification web request', request=request)

            signal_sent = self._event_handler.on_identify_requested()

            result = 'Identification signal sent' if signal_sent else 'Failed to send identification signal'

            return render_template(
                'operation.html',
                hostname=self._hostname,
                identify_result=result,
                restart_result='...'
            )

        @self._app.route('/web/restart', methods=['POST'])
        def restart_by_web() -> str:
            log.info('Restart client web request', request=request)

            restart_requested = self._event_handler.on_restart_requested()

            result = 'Restarted client mode' if restart_requested else 'Failed to restart client mode'

            return render_template(
                'operation.html',
                hostname=self._hostname,
                identify_result='...',
                restart_result=result
            )

    def _set_up_execution_web_endpoints(self) -> None:

        @self._app.route('/web/execution', methods=['GET'])
        def get_execution_page() -> str:
            log.info('Execution page', request=request)

            return render_template(
                'execution.html',
                hostname=self._hostname,
                commands=self._commands
            )

        @self._app.route('/web/execute', methods=['POST'])
        def execute_by_web() -> str:
            log.info('Execution web request', request=request)

            command = request.form['command']

            try:
                output = self._platform.execute_command(command)
                code = 0
            except CalledProcessError as error:
                output = error.stderr
                code = error.returncode

            return render_template(
                'execution.html',
                hostname=self._hostname,
                commands=self._commands,
                command=command,
                output=output.decode('utf-8') if output else '',
                code=code
            )
