# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from typing import Any, Optional

import dbus
from dbus import SystemBus, Interface, DBusException

from wifi_config import WifiNetwork
from wifi_dbus import IWifiDbus, ServiceError, PropertyError, InterfaceError


class WpaSupplicantDbus(IWifiDbus):

    def __init__(self, interface: str, system_bus: SystemBus) -> None:
        self._interface = interface
        self._system_bus = system_bus
        self._dbus_interface = WpaSupplicantInterface(interface, system_bus)
        self._dbus_network = WpaSupplicantNetwork(system_bus)

    def get_interface(self) -> str:
        return self._interface

    def add_connection_handler(self, on_connection_changed: Any) -> None:
        self._system_bus.add_signal_receiver(on_connection_changed,
                                             dbus_interface=self._dbus_interface.INTERFACE_NAME,
                                             signal_name='PropertiesChanged',
                                             path=self._dbus_interface.get_interface_path())

    def get_active_ssid(self) -> Optional[str]:
        self._dbus_interface.initialize()
        current_network_path = self._dbus_interface.get_current_network()
        if current_network_path != '/':
            return str(self._dbus_network.get_network_ssid(current_network_path))
        else:
            return None

    def add_network(self, network: WifiNetwork) -> None:
        self._dbus_interface.initialize()

        network_properties = {
            'ssid': network.ssid,
            'psk': network.password,
            'disabled': str(int(not network.enabled)),
            'priority': str(network.priority)
        }
        self._dbus_interface.add_network(network_properties)


class WpaSupplicant(object):
    _BASE_NAME = 'fi.w1.wpa_supplicant1'
    _BASE_PATH = '/fi/w1/wpa_supplicant1'

    def __init__(self, system_bus: SystemBus) -> None:
        self._system_bus = system_bus

    def __get_interface(self) -> Interface:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._BASE_PATH)
            return Interface(obj, self._BASE_NAME)
        except DBusException as error:
            raise ServiceError(error)

    def __get_properties(self) -> Any:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._BASE_PATH)
            properties_interface = Interface(obj, dbus.PROPERTIES_IFACE)
            return properties_interface.GetAll(self._BASE_NAME)
        except DBusException as error:
            raise ServiceError(error)

    def __get_property(self, property_name: str) -> Any:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._BASE_PATH)
            properties_interface = Interface(obj, dbus.PROPERTIES_IFACE)
            return properties_interface.Get(self._BASE_NAME, property_name)
        except DBusException as error:
            raise PropertyError(error)

    def __set_property(self, property_name: str, property_value: Any) -> None:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._BASE_PATH)
            properties_interface = Interface(obj, dbus.PROPERTIES_IFACE)
            properties_interface.Set(self._BASE_NAME, property_name, property_value)
        except DBusException as error:
            raise PropertyError(error)

    def get_interface(self, interface: str) -> Any:
        wpa_interface = self.__get_interface()
        try:
            return wpa_interface.GetInterface(interface)
        except DBusException as error:
            if "InterfaceUnknown" in error.get_dbus_name():
                self.create_interface(interface)
            else:
                raise InterfaceError(error)

    def create_interface(self, interface: str, bridge_interface: Optional[str] = None,
                         driver: Optional[str] = None, config_file: Optional[str] = None) -> Any:
        try:
            wpa_interface = self.__get_interface()
        except DBusException as error:
            raise ServiceError(error)
        else:
            args = {"Ifname": interface}
            if bridge_interface:
                args["BridgeIfname"] = bridge_interface
            if driver:
                args["Driver"] = driver
            if config_file:
                args["ConfigFile"] = config_file
            try:
                return wpa_interface.CreateInterface(dbus.Dictionary(args, 'sv'))
            except DBusException as error:
                raise InterfaceError(error)

    def remove_interface(self, iface_path: str) -> Any:
        try:
            wpa_interface = self.__get_interface()
        except DBusException as error:
            raise ServiceError(error)
        else:
            try:
                return wpa_interface.RemoveInterface(iface_path)
            except DBusException as error:
                raise InterfaceError(error)

    def get_interfaces(self) -> Any:
        return self.__get_property(dbus.String("Interfaces"))

    def get_eap_methods(self) -> Any:
        return self.__get_property(dbus.String("EapMethods"))

    def get_capabilities(self) -> Any:
        return self.__get_property(dbus.String("Capabilities"))

    def get_wfdies(self) -> Any:
        return self.__get_property(dbus.String("WFDIEs"))

    def set_wfdies(self, parameter: str) -> None:
        self.__set_property(dbus.String("WFDIEs"), dbus.Array(parameter, "y"))

    def show_wpa_supplicant_properties(self) -> Any:
        return self.__get_properties()


class WpaSupplicantInterface(WpaSupplicant):
    INTERFACE_NAME = "fi.w1.wpa_supplicant1.Interface"
    _DEFAULT_INTERFACE_PATH = "/fi/w1/wpa_supplicant1/Interfaces/0"

    def __init__(self, interface: str, system_bus: SystemBus) -> None:

        super(WpaSupplicantInterface, self).__init__(system_bus)
        self._interface_path = self._DEFAULT_INTERFACE_PATH
        self.interface = interface

    def initialize(self) -> None:
        self._interface_path = self.get_interface_path()

    def __get_interface(self) -> dbus.Interface:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._interface_path)
            return dbus.Interface(obj, self.INTERFACE_NAME)
        except DBusException as error:
            raise InterfaceError(error)

    def __get_property(self, property_name: str) -> Any:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._interface_path)
            properties_interface = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            return properties_interface.Get(self.INTERFACE_NAME, property_name)
        except DBusException as error:
            raise PropertyError(error)

    def __set_property(self, property_name: str, property_value: Any) -> None:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, self._interface_path)
            properties_interface = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            properties_interface.Set(self.INTERFACE_NAME, property_name, property_value)
        except DBusException as error:
            raise PropertyError(error)

    def get_interface_path(self) -> Any:
        try:
            return self.get_interface(self.interface)
        except InterfaceError:
            return self._DEFAULT_INTERFACE_PATH

    def scan(self) -> Any:
        interface = self.__get_interface()
        try:
            return interface.Scan(dbus.Dictionary({"Type": "passive"}, 'sv'))
        except DBusException as error:
            raise ServiceError(error)

    def add_network(self, network: dict[str, str]) -> Any:
        interface = self.__get_interface()
        try:
            return interface.AddNetwork(dbus.Dictionary(network, 'sv'))
        except DBusException as error:
            raise ServiceError(error)

    def remove_network(self, network_path: str) -> Any:
        interface = self.__get_interface()
        try:
            interface.RemoveNetwork(network_path)
        except DBusException as error:
            raise ServiceError(error)

    def remove_all_networks(self) -> Any:
        interface = self.__get_interface()
        try:
            interface.RemoveAllNetworks()
        except DBusException as error:
            raise ServiceError(error)

    def select_network(self, network_path: str) -> Any:
        interface = self.__get_interface()
        try:
            interface.SelectNetwork(network_path)
        except DBusException as error:
            raise ServiceError(error)

    def network_reply(self, network_path: str, parameter: str, value: str) -> Any:
        interface = self.__get_interface()
        try:
            interface.NetworkReply(network_path, parameter, value)
        except DBusException as error:
            raise ServiceError(error)

    def signal_poll(self) -> Any:
        interface = self.__get_interface()
        try:
            return interface.SignalPoll()
        except DBusException as error:
            raise ServiceError(error)

    def reassociate(self) -> Any:
        interface = self.__get_interface()
        try:
            interface.Reassociate()
        except DBusException as error:
            if "NotConnected" in error.get_dbus_name():
                pass
            else:
                raise ServiceError(error)

    def reconnect(self) -> Any:
        interface = self.__get_interface()
        try:
            interface.Reconnect()
        except DBusException as error:
            raise ServiceError(error)

    def disconnect(self) -> Any:
        interface = self.__get_interface()
        try:
            interface.Disconnect()
        except DBusException as error:
            raise ServiceError(error)

    def get_state(self) -> Any:
        return self.__get_property("State")

    def get_current_BSS(self) -> Any:
        return self.__get_property("CurrentBSS")

    def get_BSSs(self) -> Any:
        return self.__get_property("BSSs")

    def get_interface_name(self) -> Any:
        return self.__get_property("Ifname")

    def get_scanning(self) -> Any:
        return self.__get_property("Scanning")

    def get_ap_scan(self) -> Any:
        return self.__get_property("ApScan")

    def set_ap_scan(self, value: int) -> None:
        return self.__set_property("ApScan", dbus.UInt32(value))

    def get_scan_interval(self) -> Any:
        return self.__get_property("ScanInterval")

    def set_scan_interval(self, value: int) -> None:
        return self.__set_property("ScanInterval", dbus.Int32(value))

    def get_current_network(self) -> Any:
        return self.__get_property("CurrentNetwork")

    def get_networks(self) -> Any:
        return self.__get_property("Networks")

    def get_disconnect_reason(self) -> Any:
        return self.__get_property("DisconnectReason")


class WpaSupplicantNetwork(WpaSupplicant):
    _NETWORK_NAME = "fi.w1.wpa_supplicant1.Network"

    def __init__(self, system_bus: SystemBus) -> None:
        super(WpaSupplicantNetwork, self).__init__(system_bus)

    def __get_properties(self, network_path: str) -> Any:
        try:
            obj = self._system_bus.get_object(self._BASE_NAME, network_path)
            properties_interface = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            return properties_interface.GetAll(self._NETWORK_NAME)
        except DBusException as error:
            raise PropertyError(error)

    def network_enable(self, network_path: str) -> Any:
        return self.__get_properties(network_path)['Enable']

    def network_properties(self, network_path: str) -> Any:
        return self.__get_properties(network_path)['Properties']

    def get_network_ssid(self, network_path: str) -> Any:
        return self.network_properties(network_path)['ssid'].strip("\"")

    def reset_wireless(self) -> None:
        pass
