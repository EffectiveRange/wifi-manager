# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import ipaddress
import socket
import subprocess

import netifaces
from context_logger import get_logger
from ping3 import ping

log = get_logger('PlatformAccess')


class IPlatformAccess(object):

    def get_platform_version(self) -> float:
        raise NotImplementedError()

    def enable_wlan_interfaces(self) -> None:
        raise NotImplementedError()

    def get_wlan_interfaces(self) -> list[str]:
        raise NotImplementedError()

    def set_wlan_power_save(self, interface: str, enable: bool) -> None:
        raise NotImplementedError()

    def get_hostname(self) -> str:
        raise NotImplementedError()

    def get_cpu_serial(self) -> str:
        raise NotImplementedError()

    def get_mac_address(self, interface: str) -> str:
        raise NotImplementedError()

    def get_ip_address(self, interface: str) -> str:
        raise NotImplementedError()

    def set_ip_address(self, interface: str, ip_address: str, netmask: str = '255.255.255.0') -> None:
        raise NotImplementedError()

    def set_up_ip_tables(self, source_range: str, destination_host: str) -> None:
        raise NotImplementedError()

    def clean_up_ip_tables(self) -> None:
        raise NotImplementedError()

    def execute_command(self, command: str) -> bytes:
        raise NotImplementedError()

    def reboot(self) -> None:
        raise NotImplementedError()

    def ping_default_gateway(self, timeout: int) -> bool:
        raise NotImplementedError()

    def ping_tunnel_endpoint(self, timeout: int) -> bool:
        raise NotImplementedError()


class PlatformAccess(IPlatformAccess):

    def get_platform_version(self) -> float:
        with open('/etc/debian_version', 'r') as file:
            return float(file.read().strip())

    def enable_wlan_interfaces(self) -> None:
        self.execute_command('rfkill unblock wlan')

    def get_wlan_interfaces(self) -> list[str]:
        return [interface for interface in netifaces.interfaces() if interface.startswith('wl')]

    def set_wlan_power_save(self, interface: str, enable: bool) -> None:
        value = 'on' if enable else 'off'
        self.execute_command(f'iw dev {interface} set power_save {value}')

    def get_hostname(self) -> str:
        return socket.gethostname()

    def get_cpu_serial(self) -> str:
        with open('/sys/firmware/devicetree/base/serial-number') as file:
            return ''.join(file.readlines()).strip().strip('\x00')[-8:]

    def get_mac_address(self, interface: str) -> str:
        return self._get_address(interface, netifaces.AF_LINK)

    def get_ip_address(self, interface: str) -> str:
        return self._get_address(interface, netifaces.AF_INET)

    def set_ip_address(self, interface: str, ip_address: str, netmask: str = '255.255.255.0') -> None:
        self.execute_command(f'ifconfig {interface} {ip_address} netmask {netmask}')

        if self.get_ip_address(interface) != ip_address:
            raise Exception(f'Failed to set IP address {ip_address} on interface {interface}')

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
            log.info('Executing command', command=command)
            return subprocess.check_output(command, stderr=subprocess.PIPE, shell=True)
        except subprocess.CalledProcessError as error:
            log.error('Error executing command', command=command, error=error.stderr)
            raise error

    def reboot(self) -> None:
        self.execute_command('reboot')

    def ping_default_gateway(self, timeout: int) -> bool:
        if gateway := netifaces.gateways().get('default'):
            if default_gateway := gateway[netifaces.AF_INET][0]:
                try:
                    return bool(ping(default_gateway, timeout=timeout))
                except Exception:
                    return False

        return False

    def ping_tunnel_endpoint(self, timeout: int) -> bool:
        if tunnel_interfaces := [interface for interface in netifaces.interfaces() if interface.startswith('tun')]:
            if tunnel_address := self.get_ip_address(tunnel_interfaces[0]):
                try:
                    tunnel_endpoint = '.'.join(tunnel_address.split('.')[:-1] + ['1'])
                    return bool(ping(tunnel_endpoint, timeout=timeout))
                except Exception:
                    return False

        return True

    def _get_address(self, interface: str, address_family: int) -> str:
        address = netifaces.ifaddresses(interface).get(address_family)
        if address:
            return str(address[0].get('addr', ''))
        else:
            return ''
