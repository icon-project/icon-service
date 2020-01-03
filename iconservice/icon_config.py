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
    ConfigKey, ICX_IN_LOOP, TERM_PERIOD, IISS_DAY_BLOCK, PREP_MAIN_PREPS,
    PREP_MAIN_AND_SUB_PREPS, PENALTY_GRACE_PERIOD, LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
    BLOCK_VALIDATION_PENALTY_THRESHOLD, BACKUP_FILES
)

default_icon_config = {
    "log": {
        "logger": "iconservice"
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
        ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
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
    ConfigKey.IISS_CALCULATE_PERIOD: IISS_DAY_BLOCK,
    ConfigKey.TERM_PERIOD: TERM_PERIOD,
    ConfigKey.INITIAL_IREP: 50_000 * ICX_IN_LOOP,
    ConfigKey.PREP_REGISTRATION_FEE: 2_000 * ICX_IN_LOOP,
    ConfigKey.PREP_MAIN_PREPS: PREP_MAIN_PREPS,
    ConfigKey.PREP_MAIN_AND_SUB_PREPS: PREP_MAIN_AND_SUB_PREPS,
    ConfigKey.DECENTRALIZE_TRIGGER: 0.002,
    ConfigKey.PENALTY_GRACE_PERIOD: PENALTY_GRACE_PERIOD,
    ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD: LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
    ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD: BLOCK_VALIDATION_PENALTY_THRESHOLD,
    ConfigKey.STEP_TRACE_FLAG: False,
    ConfigKey.PRECOMMIT_DATA_LOG_FLAG: False,
    ConfigKey.BACKUP_FILES: BACKUP_FILES
}
