# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import fileinput

from common_utility import create_file
from context_logger import get_logger

from wifi_service import Service, ServiceDependencies

log = get_logger('AvahiService')


class AvahiService(Service):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/avahi_2ddaemon_2eservice'

    def __init__(
        self,
        dependencies: ServiceDependencies,
        hostname: str,
        hosts_config: str = '/etc/hosts',
        hostname_config: str = '/etc/hostname',
    ) -> None:
        super().__init__('avahi-daemon', self._SYSTEMD_DBUS_PATH, dependencies)
        self._hostname = hostname
        self._hosts_config = hosts_config
        self._hostname_config = hostname_config

    def _need_config_setup(self) -> bool:
        return self._platform.get_hostname() != self._hostname

    def _setup_config(self) -> None:
        current_hostname = self._platform.get_hostname()

        create_file(self._hostname_config, self._hostname + '\n')

        self._platform.execute_command(f'hostname -F {self._hostname_config}')

        with fileinput.FileInput(self._hosts_config, inplace=True) as file:
            for line in file:
                print(line.replace(current_hostname, self._hostname), end='')

        log.info('Updated hostname', old_hostname=current_hostname, new_hostname=self._hostname)
