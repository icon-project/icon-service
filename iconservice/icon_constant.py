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

from enum import IntFlag

ICON_SERVICE_LOG_TAG = 'IconService'
ICON_EXCEPTION_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Exception'
ICON_DEPLOY_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Deploy'
ICON_LOADER_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Loader'
ICX_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Icx'
ICON_DB_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_DB'
ICON_INNER_LOG_TAG = f'IconInnerService'

JSONRPC_VERSION = '2.0'
CHARSET_ENCODING = 'utf-8'

# 32bytes == 256bit
DEFAULT_BYTE_SIZE = 32
DATA_BYTE_ORDER = 'big'  # big endian
# Fixed fee is 0.01 icx.
FIXED_FEE = 10 ** 16

ICON_DEX_DB_NAME = 'icon_dex'

ICON_SCORE_QUEUE_NAME_FORMAT = "IconScore.{channel_name}.{amqp_key}"
DEFAULT_ICON_SERVICE_FOR_TBEARS_ARGUMENT = {'icon_score_root_path': '.score',
                                            'icon_score_state_db_root_path': '.db',
                                            'channel': 'tbears_channel',
                                            'amqp_key': 'amqp_key',
                                            'amqp_target': '127.0.0.1'}

ICON_SERVICE_PROCTITLE_FORMAT = "icon_service.{type}." \
                                "{iconScoreRootPath}." \
                                "{iconScoreStateDbRootPath}." \
                                "{channel}.{amqpKey}." \
                                "{amqpTarget}." \
                                "{config}"


class ConfigKey:
    BIG_STOP_LIMIT = 'iconServiceBigStepLimit'
    LOGGER_DEV = 'loggerDev'
    ADMIN_ADDRESS = 'adminAddress'
    ENABLE_THREAD_FLAG = 'enableThreadFlag'
    ICON_SERVICE_FLAG = 'iconServiceFlag'


class EnableThreadFlag(IntFlag):
    NonFlag = 0
    Invoke = 1
    Query = 2
    Validate = 4


class IconServiceFlag(IntFlag):
    NONE = 0
    ENABLE_FEE = 1
    ENABLE_AUDIT = 2


class IconDeployFlag(IntFlag):
    NONE = 0
    # To complete to install or update a SCORE,
    # some specified address owner like genesis address owner
    # MUST approve install or update SCORE transactions.
    ENABLE_DEPLOY_AUDIT = 1
