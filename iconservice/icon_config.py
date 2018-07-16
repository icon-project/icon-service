# Copyright 2017-2018 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from .icon_constant import ConfigKey
from .logger.logger import Logger


class Configure:
    def __init__(self, config_path: str):
        self._config_table = dict()
        try:
            self._init_default_table()
            with open(config_path) as f:
                json_conf = json.load(f)
                json_conf = json_conf['config']
                self._load_json_config(json_conf)
                Logger.error(f"load json success {config_path}")
        except (OSError, IOError):
            Logger.error(f"load json fail {config_path}")
            self._init_default_table()

    def _init_default_table(self) -> None:
        self._config_table[ConfigKey.BIG_STOP_LIMIT] = 5000000
        self._config_table[ConfigKey.LOGGER_DEV] = True
        self._config_table[ConfigKey.ADMIN_ADDRESS_STR] = None
        self._config_table[ConfigKey.ENABLE_THREAD_FLAG] = 0
        self._config_table[ConfigKey.ICON_SERVICE_FLAG] = 0

    def _load_json_config(self, json_conf: dict) -> None:
        for key, value in json_conf.items():
            if key in self._config_table:
                self._config_table[key] = value

    def get_value(self, key: str):
        return self._config_table.get(key, None)
