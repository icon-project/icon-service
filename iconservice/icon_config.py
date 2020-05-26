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

from .icon_constant import (
    ConfigKey, TERM_PERIOD, IISS_DAY_BLOCK, PREP_MAIN_PREPS,
    PREP_MAIN_AND_SUB_PREPS, PENALTY_GRACE_PERIOD, LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
    BLOCK_VALIDATION_PENALTY_THRESHOLD, BACKUP_FILES, BLOCK_INVOKE_TIMEOUT_S,
    IISS_INITIAL_IREP, PREP_REGISTRATION_FEE)

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
}


def normalize_input_config_fields(src_conf: dict, default_conf: dict) -> (bool, dict):
    """normalize icon configuration input.
    Returns (True, dict) if succeeded to normalize and returns (False, dict) if failed.
    Remove nonexistent keys in default config.
    """
    invalid_key_info, invalid_input_info = [], []
    update_invalid_key_info(src_conf, default_conf, invalid_key_info)
    update_invalid_input_info(src_conf, default_conf, invalid_input_info)
    is_success = True if invalid_input_info == [] else False
    invalid_fields_info = {
        "invalidKeys": invalid_key_info,
        "invalidInputs": invalid_input_info
    }
    remove_invalid_keys(src_conf, invalid_key_info)
    return is_success, invalid_fields_info


def update_invalid_key_info(src_conf: dict, default_conf: dict, invalid_key_info: list):
    for key in src_conf:
        if key not in default_conf:
            invalid_key_info.append(key)
        elif isinstance(default_conf.get(key), dict):
            src_config = src_conf.get(key, {})
            nested_invalid_info = {key: []}
            update_invalid_key_info(src_config, default_conf[key], nested_invalid_info[key])
            if nested_invalid_info[key]:
                invalid_key_info.append(nested_invalid_info)


def update_invalid_input_info(src_conf: dict, default_conf: dict, invalid_input_info: list):
    for key in src_conf:
        default_conf_value = default_conf.get(key)
        if isinstance(default_conf_value, dict):
            src_config = src_conf.get(key, {})
            nested_invalid_info = {key: []}
            update_invalid_input_info(src_config, default_conf_value, nested_invalid_info[key])
            if nested_invalid_info[key]:
                invalid_input_info.append(nested_invalid_info)
        elif default_conf_value is not None and not isinstance(src_conf[key], type(default_conf_value)):
            invalid_input_info.append(key)


def remove_invalid_keys(icon_config: dict, invalid_key_info: list):
    for element in invalid_key_info:
        if isinstance(element, dict):
            for dict_key in element:
                remove_invalid_keys(icon_config.get(dict_key, {}), element[dict_key])
        else:
            if icon_config.get(element) is not None:
                icon_config.pop(element)
