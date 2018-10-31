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
from .icon_constant import ConfigKey


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
    ConfigKey.SERVICE: {
        ConfigKey.SERVICE_FEE: False,
        ConfigKey.SERVICE_AUDIT: False,
        ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
        ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False
    }
}
