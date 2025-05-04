from os.path import exists
from pathlib import Path

from common_utility import is_file_matches_pattern, append_file, create_file, replace_in_file
from context_logger import get_logger

from wifi_utility import IPlatformAccess

log = get_logger('PlatformConfig')


class IPlatformConfig(object):

    def setup(self, disable_power_save: bool, disable_roaming: bool) -> bool:
        raise NotImplementedError()


class PlatformConfig(IPlatformConfig):

    def __init__(self, platform: IPlatformAccess, interface: str, boot_config_file: str = '/boot/config.txt',
                 driver_config_file: str = '/etc/modprobe.d/brcmfmac.conf') -> None:
        self._platform = platform
        self._interface = interface
        self._boot_config_file = boot_config_file
        self._driver_config_file = driver_config_file
        self._bluetooth_disable_config = 'dtoverlay=disable-bt'
        self._roaming_disable_config = 'options brcmfmac roamoff=1'

    def setup(self, disable_power_save: bool, disable_roaming: bool) -> bool:
        need_reboot = False
        log.info('Setting up platform config')

        if self._is_bluetooth_enabled():
            self._disable_bluetooth()
            need_reboot = True
        else:
            log.info('Bluetooth is already disabled', file=self._boot_config_file)

        if disable_power_save:
            log.info('Disabling Wi-Fi power saving')
            self._platform.set_wlan_power_save(self._interface, False)
        else:
            log.info('Enabling Wi-Fi power saving')
            self._platform.set_wlan_power_save(self._interface, True)

        if self._is_roaming_enabled():
            if disable_roaming:
                self._disable_roaming()
                need_reboot = True
            else:
                log.info('Wi-Fi roaming is already enabled', file=self._driver_config_file)
        else:
            if not disable_roaming:
                self._enable_roaming()
                need_reboot = True
            else:
                log.info('Wi-Fi roaming is already disabled', file=self._driver_config_file)

        return need_reboot

    def _is_bluetooth_enabled(self) -> bool:
        return not is_file_matches_pattern(self._boot_config_file, self._bluetooth_disable_config)

    def _is_roaming_enabled(self) -> bool:
        return not is_file_matches_pattern(self._driver_config_file, self._roaming_disable_config)

    def _disable_bluetooth(self) -> None:
        log.info('Disabling Bluetooth in boot config',
                 file=self._boot_config_file, config=self._bluetooth_disable_config)
        self._create_or_append_file(self._boot_config_file, self._bluetooth_disable_config)

    def _disable_roaming(self) -> None:
        log.info('Disabling Wi-Fi roaming in driver config',
                 file=self._driver_config_file, config=self._roaming_disable_config)
        self._create_or_append_file(self._driver_config_file, self._roaming_disable_config)

    def _enable_roaming(self) -> None:
        log.info('Removing Wi-Fi roaming flag from driver config',
                 file=self._driver_config_file, config=self._roaming_disable_config)
        self._delete_line(self._driver_config_file, self._roaming_disable_config)

    def _create_or_append_file(self, file_path: str, line: str) -> None:
        if exists(file_path):
            content = Path(file_path).read_text(encoding='utf-8')
            has_new_line = content.endswith('\n') if content else True
            append_file(file_path, line if has_new_line else f'\n{line}')
        else:
            create_file(file_path, line)

    def _delete_line(self, file_path: str, line: str) -> None:
        if exists(file_path):
            replace_in_file(file_path, f'{line}\n', '')
