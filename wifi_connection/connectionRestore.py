# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import Optional

from context_logger import get_logger
from systemd_dbus import Systemd

from wifi_service import WifiClientService
from wifi_utility import IPlatformAccess

log = get_logger('ConnectionRestore')


class ActionType(Enum):
    RESET_WIRELESS = 'reset-wireless'
    RESTART_SERVICE = 'restart-service'
    EXECUTE_COMMAND = 'execute-command'

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def to_action_type(action_name: str) -> Optional['ActionType']:
        for action_type in ActionType:
            if action_name == action_type.value:
                return action_type
        return None


class ConnectionRestoreAction(object):

    @classmethod
    def create_actions(cls, action_strings: list[str], client: WifiClientService, systemd: Systemd,
                       platform: IPlatformAccess) -> list['ConnectionRestoreAction']:
        actions: list[ConnectionRestoreAction] = []

        for action_string in action_strings:
            action_parts = action_string.split(' ', 1)
            action_name = action_parts[0]
            action_value = action_parts[1] if len(action_parts) > 1 else None

            if action_type := ActionType.to_action_type(action_name):
                if action_type == ActionType.RESET_WIRELESS:
                    actions.append(ResetWirelessAction(client))
                elif action_type == ActionType.RESTART_SERVICE and action_value:
                    actions.append(RestartServiceAction(systemd, action_value))
                elif action_type == ActionType.EXECUTE_COMMAND and action_value:
                    actions.append(ExecuteCommandAction(platform, action_value))

        return actions

    def __init__(self, action_type: ActionType) -> None:
        self._action_type = action_type

    def run(self) -> None:
        raise NotImplementedError()


class ResetWirelessAction(ConnectionRestoreAction):

    def __init__(self, client: WifiClientService) -> None:
        super().__init__(ActionType.RESET_WIRELESS)
        self._client = client

    def run(self) -> None:
        self._client.reset_wireless()
        log.info('Reset wireless connection')


class RestartServiceAction(ConnectionRestoreAction):

    def __init__(self, systemd: Systemd, service: str) -> None:
        super().__init__(ActionType.RESTART_SERVICE)
        self._systemd = systemd
        self._service = service

    def run(self) -> None:
        for service in self._systemd.list_service_names(patterns=[self._service]):
            self._systemd.restart_service(service)
            log.info('Restarted service', service=service)


class ExecuteCommandAction(ConnectionRestoreAction):

    def __init__(self, platform: IPlatformAccess, command: str) -> None:
        super().__init__(ActionType.EXECUTE_COMMAND)
        self._platform = platform
        self._command = command

    def run(self) -> None:
        self._platform.execute_command(self._command)
        log.info('Executed command', command=self._command)
