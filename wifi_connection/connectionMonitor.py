# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT
import os
from dataclasses import dataclass
from pathlib import Path

from common_utility import IReusableTimer
from context_logger import get_logger
from systemd_dbus import Systemd

from wifi_connection import ConnectionAction, RestartServiceAction
from wifi_utility import IPlatformAccess

log = get_logger('ConnectionMonitor')


@dataclass
class ConnectionMonitorConfig:
    config_dir: Path
    ping_interval: int
    ping_timeout: int
    ping_fail_limit: int
    connect_actions: list[ConnectionAction]
    restore_actions: list[ConnectionAction]


class IConnectionMonitor(object):

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class ConnectionMonitor(IConnectionMonitor):

    def __init__(self, platform: IPlatformAccess, systemd: Systemd, timer: IReusableTimer,
                 config: ConnectionMonitorConfig):
        self._platform = platform
        self._systemd = systemd
        self._timer = timer
        self._config = config
        self._failures = 0
        self._restart_dir = config.config_dir / 'restart.d'

    def start(self) -> None:
        self._failures = 0
        self._timer.start(self._config.ping_interval, self._check_connection)

        log.info("Connection established, executing connect actions")
        self._run_actions(self._get_connect_actions())

    def stop(self) -> None:
        self._timer.cancel()

    def _check_connection(self) -> None:
        if self._platform.ping_default_gateway(self._config.ping_timeout):
            if self._platform.ping_tunnel_endpoint(self._config.ping_timeout):
                if self._failures > 0:
                    self._failures = 0
                    log.info("Connection restored, executing connect actions")
                    self._run_actions(self._get_connect_actions())
            else:
                self._failures += 1
                log.warn("Ping to tunnel endpoint failed", failures=self._failures, timeout=self._config.ping_timeout)

        else:
            self._failures += 1
            log.warn("Ping to default gateway failed", failures=self._failures, timeout=self._config.ping_timeout)

        if self._failures >= self._config.ping_fail_limit:
            self._failures = 0
            log.error("Failed to reach default gateway or tunnel endpoint, executing restore actions")

            self._run_actions(self._config.restore_actions)

        self._timer.restart()

    def _run_actions(self, actions: list[ConnectionAction]) -> None:
        for action in actions:
            action.run()

    def _get_connect_actions(self) -> list[ConnectionAction]:
        services = os.listdir(str(self._restart_dir))
        restart_actions = [RestartServiceAction(self._systemd, service) for service in services]

        connect_actions = self._config.connect_actions + restart_actions

        return connect_actions
