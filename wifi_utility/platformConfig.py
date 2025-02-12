from os.path import exists
from pathlib import Path

from common_utility import is_file_matches_pattern, append_file, create_file
from context_logger import get_logger

log = get_logger('PlatformConfig')


class IPlatformConfig(object):

    def setup(self) -> bool:
        raise NotImplementedError()


class PlatformConfig(IPlatformConfig):

    def __init__(self, boot_config_file: str = '/boot/config.txt',
                 driver_config_file: str = '/etc/modprobe.d/brcmfmac.conf') -> None:
        self._boot_config_file = boot_config_file
        self._driver_config_file = driver_config_file
        self._bluetooth_disable_config = 'dtoverlay=disable-bt'
        self._wifi_roam_disable_config = 'options brcmfmac roamoff=1'

    def setup(self) -> bool:
        need_reboot = False
        log.info('Setting up platform config')

        if self._is_bluetooth_enabled():
            self._disable_bluetooth()
            need_reboot = True
        else:
            log.info('Bluetooth is already disabled', file=self._boot_config_file)

        if self._is_wifi_roam_enabled():
            self._disable_wifi_roam()
            need_reboot = True
        else:
            log.info('Wi-Fi roaming is already disabled', file=self._driver_config_file)

        return need_reboot

    def _is_bluetooth_enabled(self) -> bool:
        return not is_file_matches_pattern(self._boot_config_file, self._bluetooth_disable_config)

    def _is_wifi_roam_enabled(self) -> bool:
        return not is_file_matches_pattern(self._driver_config_file, self._wifi_roam_disable_config)

    def _disable_bluetooth(self) -> None:
        log.info('Disabling Bluetooth in boot config',
                 file=self._boot_config_file, config=self._bluetooth_disable_config)
        self._create_or_append_file(self._boot_config_file, self._bluetooth_disable_config)

    def _disable_wifi_roam(self) -> None:
        log.info('Disabling Wi-Fi roaming in driver config',
                 file=self._driver_config_file, config=self._wifi_roam_disable_config)
        self._create_or_append_file(self._driver_config_file, self._wifi_roam_disable_config)

    def _create_or_append_file(self, file_path: str, line: str) -> None:
        if exists(file_path):
            content = Path(file_path).read_text(encoding="utf-8")
            has_new_line = content.endswith("\n") if content else True
            append_file(file_path, line if has_new_line else f'\n{line}')
        else:
            create_file(file_path, line)
