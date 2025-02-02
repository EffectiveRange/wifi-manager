# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import ipaddress
import socket
import subprocess

import netifaces
from context_logger import get_logger

log = get_logger('Platform')


class IPlatform(object):

    def enable_wlan_interfaces(self) -> None:
        raise NotImplementedError()

    def get_wlan_interfaces(self) -> list[str]:
        raise NotImplementedError()

    def disable_wlan_power_save(self, interface: str) -> None:
        raise NotImplementedError()

    def get_hostname(self) -> str:
        raise NotImplementedError()

    def get_cpu_serial(self) -> str:
        raise NotImplementedError()

    def get_mac_address(self, interface: str) -> str:
        raise NotImplementedError()

    def get_ip_address(self, interface: str) -> str:
        raise NotImplementedError()

    def set_up_ip_tables(self, source_range: str, destination_host: str) -> None:
        raise NotImplementedError()

    def clean_up_ip_tables(self) -> None:
        raise NotImplementedError()

    def execute_command(self, command: str) -> bytes:
        raise NotImplementedError()


class Platform(IPlatform):

    def enable_wlan_interfaces(self) -> None:
        self.execute_command('rfkill unblock wlan')

    def get_wlan_interfaces(self) -> list[str]:
        return [interface for interface in netifaces.interfaces() if interface.startswith('wl')]

    def disable_wlan_power_save(self, interface: str) -> None:
        self.execute_command(f'iw dev {interface} set power_save off')

    def get_hostname(self) -> str:
        return socket.gethostname()

    def get_cpu_serial(self) -> str:
        with open('/sys/firmware/devicetree/base/serial-number') as file:
            return ''.join(file.readlines()).strip().strip('\x00')[-8:]

    def get_mac_address(self, interface: str) -> str:
        return self._get_address(interface, netifaces.AF_LINK)

    def get_ip_address(self, interface: str) -> str:
        return self._get_address(interface, netifaces.AF_INET)

    def set_up_ip_tables(self, ip_address: str, destination_host: str) -> None:
        source_range = str(ipaddress.IPv4Network(address=f'{ip_address}/255.255.255.0', strict=False))
        command = (f'iptables -t nat -A PREROUTING '
                   f'-s {source_range} -p tcp -m tcp --dport 80 -j DNAT --to-destination {destination_host}')
        self.execute_command(command)

        command = 'iptables -t nat -A POSTROUTING -j MASQUERADE'
        self.execute_command(command)

    def clean_up_ip_tables(self) -> None:
        command = 'iptables -t nat -F && iptables -t nat -X'
        self.execute_command(command)

    def execute_command(self, command: str) -> bytes:
        try:
            return subprocess.check_output(command, stderr=subprocess.PIPE, shell=True)
        except subprocess.CalledProcessError as error:
            log.error('Error executing command', command=command, error=error.stderr)
            raise error

    def _get_address(self, interface: str, address_family: int) -> str:
        address = netifaces.ifaddresses(interface).get(address_family)
        if address:
            return str(address[0].get('addr', ''))
        else:
            return ''
