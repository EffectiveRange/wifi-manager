# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from context_logger import get_logger

from wifi_utility import IPlatformAccess

log = get_logger('InterfaceSelector')


class InterfaceSelector(object):

    def select(self, interface: str) -> str:
        raise NotImplementedError()


class WlanInterfaceSelector(InterfaceSelector):

    def __init__(self, platform: IPlatformAccess):
        self._platform = platform

    def select(self, interface: str) -> str:
        self._platform.enable_wlan_interfaces()

        interfaces = self._platform.get_wlan_interfaces()

        if not interfaces:
            raise ValueError('No wireless interfaces found')

        if interface not in interfaces:
            selected_interface = interfaces[0]
            log.warning('Specified interface not found, using first available',
                        interfaces=interfaces, specified=interface, selected=selected_interface)
            return selected_interface
        else:
            log.info('Selected specified interface', interfaces=interfaces, selected=interface)
            return interface
