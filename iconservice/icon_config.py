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
from .icon_constant import ConfigKey, ICX_IN_LOOP, IISS_DAY_BLOCK

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
    ConfigKey.IISS_CALCULATE_PERIOD: IISS_DAY_BLOCK,
    ConfigKey.TERM_PERIOD: IISS_DAY_BLOCK,
    ConfigKey.INITIAL_IREP: 50_000 * ICX_IN_LOOP,
    ConfigKey.PREP_REGISTRATION_FEE: 2_000 * ICX_IN_LOOP,
    ConfigKey.PREP_MAIN_PREPS: 22,
    ConfigKey.PREP_MAIN_AND_SUB_PREPS: 100,
    ConfigKey.DECENTRALIZE_TRIGGER: 0.002
}
