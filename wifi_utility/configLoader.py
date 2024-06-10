# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import configparser
import os
import shutil
from pathlib import Path
from typing import Any

from context_logger import get_logger

log = get_logger('ConfigurationLoader')


class IConfigLoader(object):

    def load(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError()


class ConfigLoader(IConfigLoader):

    def __init__(self, resource_root: str):
        self._resource_root = resource_root

    def load(self, arguments: dict[str, Any]) -> dict[str, Any]:
        config_file = Path(arguments['config_file'])

        if not os.path.exists(config_file):
            log.info('Creating default configuration file', config_file=str(config_file))
            default_config = f'{self._resource_root}/config/wifi-manager.conf'
            config_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(default_config, config_file)
        else:
            log.info('Using existing configuration file', config_file=str(config_file))

        parser = configparser.ConfigParser()
        parser.read(config_file)

        configuration = dict(parser['DEFAULT'])
        configuration.update(arguments)

        return configuration
