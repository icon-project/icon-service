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

default_icon_config = {
    "log": {
        "colorLog": True,
        "level": "debug",
        "filePath": "./log/icon_service1.log",
        "outputType": "console|file|daily"
    },
    "iconScoreRootPath": ".score",
    "iconScoreStateDbRootPath": ".db",
    "channel": "loopchain_default",
    "amqpKey": "7100",
    "amqpTarget": "127.0.0.1",
    "iconServiceBigStopLimit": 5000000,
    "loggerDev": True,
    "adminAddress": "hxebf3a409845cd09dcb5af31ed5be5e34e2af9433",
    "enableThreadFlag": 0,
    "iconServiceFlag": 0
}
