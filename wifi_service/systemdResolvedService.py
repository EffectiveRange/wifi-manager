# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from context_logger import get_logger

from wifi_service import Service, ServiceDependencies

log = get_logger('SystemdResolvedService')


class SystemdResolvedService(Service):
    _SYSTEMD_DBUS_PATH = '/org/freedesktop/systemd1/unit/systemd_2dresolved_2eservice'

    def __init__(self, dependencies: ServiceDependencies) -> None:
        super().__init__('systemd-resolved', self._SYSTEMD_DBUS_PATH, dependencies)

    def _auto_start(self) -> bool:
        return False

    def _force_stop(self) -> bool:
        return True
