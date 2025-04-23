# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

from common_utility import IReusableTimer
from context_logger import get_logger

from wifi_connection import ConnectionRestoreAction
from wifi_utility import IPlatformAccess

log = get_logger('ConnectionMonitor')


@dataclass
class ConnectionMonitorConfig:
    ping_interval: int
    ping_timeout: int
    ping_fail_limit: int
    restore_actions: list[ConnectionRestoreAction]


class IConnectionMonitor(object):

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class ConnectionMonitor(IConnectionMonitor):

    def __init__(self, platform: IPlatformAccess, timer: IReusableTimer, config: ConnectionMonitorConfig):
        self._platform = platform
        self._timer = timer
        self._config = config
        self._failures = 0

    def start(self) -> None:
        self._timer.start(self._config.ping_interval, self._check_connection)

    def stop(self) -> None:
        self._timer.cancel()

    def _check_connection(self) -> None:
        if self._platform.ping_default_gateway(self._config.ping_timeout):
            self._failures = 0
        else:
            self._failures += 1
            log.warn("Ping to default gateway failed", failures=self._failures, timeout=self._config.ping_timeout)

            if self._failures >= self._config.ping_fail_limit:
                self._failures = 0
                log.error("Failed to reach default gateway, executing restore actions")

                for action in self._config.restore_actions:
                    action.run()

        self._timer.restart()
