# Copyright 2018 ICON Foundation
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

import copy
from typing import Dict, Union, List, Type, Optional

from iconcommons.logger import Logger

from .base.exception import InternalServiceErrorException
from .icon_constant import (
    ConfigKey, TERM_PERIOD, IISS_DAY_BLOCK, PREP_MAIN_PREPS,
    PREP_MAIN_AND_SUB_PREPS, PENALTY_GRACE_PERIOD, LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
    BLOCK_VALIDATION_PENALTY_THRESHOLD, BACKUP_FILES, BLOCK_INVOKE_TIMEOUT_S,
    IISS_INITIAL_IREP, PREP_REGISTRATION_FEE, UNSTAKE_SLOT_MAX)

_TAG = "CFG"
ConfigValue = Union[bool, dict, float, int, str]
ConfigKeyTypeDict = Dict[str, Union[dict, Type[Union[bool, float, int, str]]]]

default_icon_config = {
    ConfigKey.LOG: {
        ConfigKey.LOGGER: "iconservice",
        ConfigKey.LOG_FILE_PATH: "./",
        ConfigKey.LOG_LEVEL: "debug"
    },
    ConfigKey.SCORE_ROOT_PATH: ".score",
    ConfigKey.STATE_DB_ROOT_PATH: ".statedb",
    ConfigKey.CHANNEL: "loopchain_default",
    ConfigKey.AMQP_KEY: "7100",
    ConfigKey.AMQP_TARGET: "127.0.0.1",
    ConfigKey.BUILTIN_SCORE_OWNER: "hxebf3a409845cd09dcb5af31ed5be5e34e2af9433",
    ConfigKey.IPC_TIMEOUT: 10,
    ConfigKey.SERVICE: {
        ConfigKey.SERVICE_FEE: False,
        ConfigKey.SERVICE_AUDIT: False,
        ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False
    },
    ConfigKey.IISS_META_DATA: {
        ConfigKey.REWARD_MIN: 200,
        ConfigKey.REWARD_MAX: 1200,
        ConfigKey.REWARD_POINT: 7000,
        ConfigKey.UN_STAKE_LOCK_MIN: IISS_DAY_BLOCK * 5,
        ConfigKey.UN_STAKE_LOCK_MAX: IISS_DAY_BLOCK * 20
    },
    # The reason why IISS_CALCULATE_PERIOD and TERM_PERIOD value is different
    # is to synchronize with the main net without revisioning.
    # In the main net, calculate period in prevote is 43_200,
    # and after decentralizing, is set to 43_120.
    # If you want to change as TERM_PERIOD, you also must change REVISION.
    # so we determined that only TERM_PERIOD changed without IISS_CALCULATE_PERIOD.
    ConfigKey.ICON_RC_DIR_PATH: "",
    ConfigKey.ICON_RC_MONITOR: True,
    ConfigKey.IISS_CALCULATE_PERIOD: IISS_DAY_BLOCK,
    ConfigKey.TERM_PERIOD: TERM_PERIOD,
    ConfigKey.INITIAL_IREP: IISS_INITIAL_IREP,
    ConfigKey.PREP_REGISTRATION_FEE: PREP_REGISTRATION_FEE,
    ConfigKey.PREP_MAIN_PREPS: PREP_MAIN_PREPS,
    ConfigKey.PREP_MAIN_AND_SUB_PREPS: PREP_MAIN_AND_SUB_PREPS,
    ConfigKey.DECENTRALIZE_TRIGGER: 0.002,
    ConfigKey.PENALTY_GRACE_PERIOD: PENALTY_GRACE_PERIOD,
    ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD: LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
    ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD: BLOCK_VALIDATION_PENALTY_THRESHOLD,
    ConfigKey.STEP_TRACE_FLAG: False,
    ConfigKey.PRECOMMIT_DATA_LOG_FLAG: False,
    ConfigKey.BACKUP_FILES: BACKUP_FILES,
    ConfigKey.BLOCK_INVOKE_TIMEOUT: BLOCK_INVOKE_TIMEOUT_S,
    ConfigKey.TBEARS_MODE: False,
    ConfigKey.UNSTAKE_SLOT_MAX: UNSTAKE_SLOT_MAX,
}


def check_config(conf: dict, default_conf: dict) -> bool:
    checker = ConfigSanityChecker(default_conf)
    ret: bool = checker.run(conf)

    if len(checker.invalid_keys) > 0:
        Logger.info(tag=_TAG, msg="===== INVALID CONFIGURATION KEYS =====")
        for item in checker.invalid_keys:
            Logger.info(tag=_TAG, msg=f"{item}")

    if len(checker.invalid_values) > 0:
        Logger.error(tag=_TAG, msg="===== INVALID CONFIGURATION VALUE TYPES ===== ")
        for item in checker.invalid_values:
            Logger.error(tag=_TAG, msg=f"{item}")

    return ret


def args_to_dict(args) -> dict:
    """Convert args to dict
    :param args: command line arguments
    :return: conf in dict containing command line arguments
    """
    keys_to_remove = {"command", "foreground", "config"}
    args_dict = vars(args)
    ret = {}

    for key, value in args_dict.items():
        if key not in keys_to_remove and value is not None:
            ret[key] = value

    return ret


class ConfigSanityChecker(object):
    """Sanity check for iconservice configuration file
    """

    class Item(object):
        def __init__(self,
                     key: str,
                     value: ConfigValue,
                     value_type: Optional[Type[ConfigValue]]):
            self._key = key
            self._value = value
            self._value_type = value_type

        @property
        def key(self) -> str:
            return self._key

        @property
        def value(self) -> ConfigValue:
            return self._value

        @property
        def value_type(self) -> Optional[Type[ConfigValue]]:
            return self._value_type

        def __str__(self) -> str:
            return f"key={self._key} value={self._value} value_type={self._value_type}"

    def __init__(self, default_conf: Dict[str, ConfigValue]):
        """
        :param default_conf: dict containing default configuration values
        """

        self._invalid_keys = []
        self._invalid_values = []
        # dict containing config_key:value_type
        self._config_key_type_dict: ConfigKeyTypeDict = self._init_config_key_type_dict(default_conf)
        self._add_extra_value_types(self._config_key_type_dict)

    @classmethod
    def _init_config_key_type_dict(cls, default_conf: dict) -> ConfigKeyTypeDict:
        config_key_type_dict = copy.deepcopy(default_conf)

        def get_value_type(value):
            if isinstance(value, dict):
                _table = value
                for key in _table:
                    _table[key] = get_value_type(_table[key])
            elif isinstance(value, (bool, float, int, str)):
                value = type(value)
            else:
                raise InternalServiceErrorException(f"Invalid default config: {value}")

            return value

        return get_value_type(config_key_type_dict)

    @classmethod
    def _add_extra_value_types(cls, table: ConfigKeyTypeDict):
        # Add some value types which cannot be contained to default_conf
        table[ConfigKey.LOG] = {
            ConfigKey.LOGGER: str,
            ConfigKey.LOG_FILE_PATH: str,
            ConfigKey.LOG_LEVEL: str,
            ConfigKey.LOG_OUTPUT_TYPE: str,
            ConfigKey.LOG_ROTATE: {
                ConfigKey.LOG_ROTATE_TYPE: str,
                ConfigKey.LOG_ROTATE_PERIOD: str,
                ConfigKey.LOG_ROTATE_AT_TIME: int,
                ConfigKey.LOG_ROTATE_INTERVAL: int,
                ConfigKey.LOG_ROTATE_MAX_BYTES: int,
                ConfigKey.LOG_ROTATE_BACKUP_COUNT: int,
            },
        }

    @property
    def invalid_keys(self) -> List[Item]:
        return self._invalid_keys

    @property
    def invalid_values(self) -> List:
        return self._invalid_values

    def run(self, conf: Dict[str, ConfigValue]) -> bool:
        self._invalid_keys.clear()
        self._invalid_values.clear()

        self._check(
            conf,
            self._config_key_type_dict,
            self._invalid_keys,
            self._invalid_values
        )

        return len(self._invalid_values) == 0

    @classmethod
    def _check(cls,
               conf: Dict[str, ConfigValue],
               key_type_table: ConfigKeyTypeDict,
               invalid_keys: List[Item],
               invalid_values: List[Item]):
        for key, value in conf.items():
            try:
                # Check if key is valid
                if key not in key_type_table:
                    raise KeyError(key, value)

                # Check if value is valid
                value_type: Type = cls._get_value_type(key_type_table, key)
                if type(value) is not value_type:
                    raise ValueError(key, value, value_type)

                if isinstance(value, dict):
                    # If value is a dict type, call _check() recursively
                    cls._check(
                        conf=value,
                        key_type_table=key_type_table[key],
                        invalid_keys=invalid_keys,
                        invalid_values=invalid_values
                    )
            except KeyError as e:
                invalid_keys.append(cls.Item(key=e.args[0], value=e.args[1], value_type=None))
            except ValueError as e:
                invalid_values.append(cls.Item(key=e.args[0], value=e.args[1], value_type=e.args[2]))

    @classmethod
    def _get_value_type(cls, key_type_table: ConfigKeyTypeDict, key: str) -> Type[ConfigValue]:
        """Returns the proper value type for configuration key from key_type_table

        :param key_type_table: key:value_type table
        :param key: configuration key
        :return: value type of a given configuration key
        """
        value_type = key_type_table[key]
        if not isinstance(value_type, type):
            # If value_type is a dict object, set type(value_type) to value_type
            value_type = type(value_type)

        return value_type
