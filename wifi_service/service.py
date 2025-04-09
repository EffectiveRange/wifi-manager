# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT
from enum import Enum
from threading import Event
from typing import Optional, Any

from context_logger import get_logger
from systemd_dbus import Systemd

from wifi_config import WifiNetwork
from wifi_event import WifiEventType
from wifi_utility import IPlatformAccess, IJournal

log = get_logger('Service')


class ServiceError(Exception):

    def __init__(self, service: str, message: str):
        super().__init__(message)
        self.service = service


class IService(object):

    def setup(self) -> None:
        raise NotImplementedError()

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()

    def restart(self) -> None:
        raise NotImplementedError()

    def set_auto_start(self, auto_start: bool) -> None:
        raise NotImplementedError()

    def set_force_stop(self, force_stop: bool) -> None:
        raise NotImplementedError()

    def is_active(self) -> bool:
        raise NotImplementedError()

    def is_enabled(self) -> bool:
        raise NotImplementedError()

    def is_installed(self) -> bool:
        raise NotImplementedError()

    def get_name(self) -> str:
        raise NotImplementedError()

    def get_supported_events(self) -> set[WifiEventType]:
        raise NotImplementedError()

    def register_state_change_handler(self) -> None:
        raise NotImplementedError()

    def register_callback(self, event: WifiEventType, callback: Any, *args: Any) -> None:
        raise NotImplementedError()


class ServiceDependencies(object):

    def __init__(self, platform: IPlatformAccess, systemd: Systemd, journal: IJournal):
        self.platform = platform
        self.systemd = systemd
        self.journal = journal


class Service(IService):

    def __init__(self, service_name: str, service_path: str, dependencies: ServiceDependencies):
        self._name = service_name
        self._path = service_path
        self._platform = dependencies.platform
        self._systemd = dependencies.systemd
        self._journal = dependencies.journal
        self._config_reloaded = Event()
        self._force_stop = False
        self._auto_start = True
        self._failed = False
        self._last_state: Optional[str] = None
        self._event_callbacks: dict[WifiEventType, Any] = {}

    def setup(self) -> None:
        try:
            self._setup_unmasking()
            self._setup_auto_start()
            self._setup_masking()
            self._setup_state_change_handling()
            self._setup_config_and_reload()
            self._setup_custom_event_handling()
        except Exception as error:
            raise ServiceError(self._name, str(error))

    def start(self) -> None:
        self._prepare_start()
        log.debug('Starting service', service=self._name)
        self._systemd.start_service(self._name)
        self._complete_start()

    def stop(self) -> None:
        log.debug('Stopping service', service=self._name)
        self._systemd.stop_service(self._name)

    def restart(self) -> None:
        self._prepare_start()
        log.debug('Restarting service', service=self._name)
        self._systemd.restart_service(self._name)
        self._complete_start()

    def set_auto_start(self, auto_start: bool) -> None:
        self._auto_start = auto_start

    def set_force_stop(self, force_stop: bool) -> None:
        self._force_stop = force_stop

    def is_active(self) -> bool:
        return self._systemd.is_active(self._name)

    def is_enabled(self) -> bool:
        return self._systemd.is_enabled(self._name)

    def is_installed(self) -> bool:
        return self._systemd.is_installed(self._name)

    def get_name(self) -> str:
        return self._name

    def get_supported_events(self) -> set[WifiEventType]:
        return set()

    def register_callback(self, event_type: WifiEventType, callback: Any, *args: Any) -> None:
        if event_type in self.get_supported_events():
            if event_type in self._event_callbacks:
                log.warning('Overwriting existing callback', service=self._name, event_type=event_type)
            self._event_callbacks[event_type] = (callback, args)
        else:
            raise ServiceError(self._name, f'Unsupported event: {event_type}')

    def _prepare_start(self) -> None:
        pass

    def _complete_start(self) -> None:
        pass

    def _is_auto_start(self) -> bool:
        return not self._force_stop and self._auto_start

    def _is_force_stop(self) -> bool:
        return self._force_stop

    def _setup_masking(self) -> None:
        if self._is_force_stop() and not self._systemd.is_masked(self._name):
            log.info('Service is unmasked, masking service', service=self._name)
            self._systemd.mask_service(self._name)
            self._systemd.reload_daemon()

    def _setup_unmasking(self) -> None:
        if not self._is_force_stop() and self._systemd.is_masked(self._name):
            log.info('Service is masked, unmasking service', service=self._name)
            self._systemd.unmask_service(self._name)
            self._systemd.reload_daemon()

    def _setup_auto_start(self) -> None:
        if self._is_auto_start():
            if not self.is_enabled():
                log.info('Service is not enabled, enabling service', service=self._name)
                self._systemd.enable_service(self._name)
            self.start()
        else:
            if self.is_enabled():
                log.info('Service is enabled, disabling service', service=self._name)
                self._systemd.disable_service(self._name)
            self.stop()

    def _setup_state_change_handling(self) -> None:
        self._add_property_change_handler(self._on_property_changed)

    def _need_config_setup(self) -> bool:
        return False

    def _setup_config(self) -> None:
        pass

    def _reload_config(self) -> None:
        self._systemd.restart_service(self._name)

    def _setup_config_and_reload(self) -> None:
        if self._need_config_setup():
            log.info('Service configuration setup required', service=self._name)
            self._setup_config()

            if self._need_config_setup():
                raise ServiceError(self._name, 'Configuration check failed after setup')

            if self._is_auto_start():
                self._reload_config()
                self._config_reloaded.wait()
        self._config_reloaded.set()

    def _setup_custom_event_handling(self) -> None:
        pass

    def _execute_callback(self, event_type: WifiEventType, event_data: Any) -> None:
        callback = self._event_callbacks.get(event_type)
        if callback:
            callback, args = callback
            try:
                callback(event_type, event_data)
            except Exception as error:
                log.error('Callback execution error for event',
                          event_type=event_type, callback=callback.__name__, service=self._name, error=error)

    def _add_property_change_handler(self, handler: Any) -> None:
        self._systemd.add_property_change_handler(self._path, handler)

    def _on_property_changed(self, *args: Any) -> None:
        _, props, _ = args
        state = props.get('ActiveState')

        if state and state != self._last_state:
            self._on_service_state_changed(state)
            self._last_state = state

    def _on_service_state_changed(self, state: str) -> None:
        log.debug('Service state changed', service=self._name, ols_state=self._last_state, new_state=state)

        if state == 'failed' and not self._failed:
            log.error('Service failed, loading journal entries', service=self._name)
            self._failed = True
            self._journal.log_last_entries(self._name, 5)
            if not self._is_force_stop():
                log.error('Service failed, restarting service', service=self._name)
                self.restart()
        elif state == 'active':
            if self._failed:
                log.info('Service restored', service=self._name)
                self._failed = False
            if not self._config_reloaded.is_set() and self._last_state == 'activating':
                log.info('Service configuration reloaded', service=self._name)
                self._config_reloaded.set()
            if self._is_force_stop():
                log.info('Force stopping service', service=self._name)
                self.stop()


class WifiService(Service):

    def get_interface(self) -> str:
        raise NotImplementedError()

    def get_ip_address(self) -> str:
        return self._platform.get_ip_address(self.get_interface())

    def get_mac_address(self) -> str:
        return self._platform.get_mac_address(self.get_interface())


class WifiClientStateEvent(Enum):
    active = WifiEventType.CLIENT_STARTED
    inactive = WifiEventType.CLIENT_STOPPED
    failed = WifiEventType.CLIENT_FAILED

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def to_wifi_event(name: str) -> Optional['WifiEventType']:
        if name in WifiClientStateEvent.__members__:
            return WifiClientStateEvent[name].value
        else:
            return None


class WifiHotspotStateEvent(Enum):
    active = WifiEventType.HOTSPOT_STARTED
    inactive = WifiEventType.HOTSPOT_STOPPED
    failed = WifiEventType.HOTSPOT_FAILED

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def to_wifi_event(name: str) -> Optional['WifiEventType']:
        if name in WifiHotspotStateEvent.__members__:
            return WifiHotspotStateEvent[name].value
        else:
            return None


class WifiClientService(WifiService):

    def get_connected_ssid(self) -> Optional[str]:
        raise NotImplementedError()

    def get_network_count(self) -> int:
        raise NotImplementedError()

    def get_networks(self) -> list[WifiNetwork]:
        raise NotImplementedError()

    def add_network(self, network: WifiNetwork) -> None:
        raise NotImplementedError()


class WifiHotspotService(WifiService):

    def get_hotspot_ssid(self) -> str:
        raise NotImplementedError()

    def get_hotspot_ip(self) -> str:
        raise NotImplementedError()


class DhcpServerService(Service):

    def get_static_ip(self) -> str:
        raise NotImplementedError()
