# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from typing import Any, Optional

from gi.repository import GLib

from wifi_config import WifiNetwork


class ServiceError(Exception):
    pass


class InterfaceError(Exception):
    pass


class PropertyError(Exception):
    pass


class IWifiDbus(object):

    def get_interface(self) -> str:
        raise NotImplementedError()

    def add_connection_handler(self, on_connection_changed: Any) -> None:
        raise NotImplementedError()

    def get_active_ssid(self) -> Optional[str]:
        raise NotImplementedError()

    def add_network(self, network: WifiNetwork) -> Any:
        raise NotImplementedError()


def bytes_to_str(glib_bytes: GLib.Bytes) -> str:
    data = glib_bytes.get_data()
    return data.decode('utf-8') if data else ''


def str_to_bytes(data: str) -> GLib.Bytes:
    return GLib.Bytes.new(data.encode())
