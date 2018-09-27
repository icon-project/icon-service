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
# Max data field size
MAX_DATA_SIZE = 512 * 1024

ICON_DEX_DB_NAME = 'icon_dex'

ICX_TRANSFER_EVENT_LOG = 'ICXTransfer(Address,Address,int)'

ICON_SCORE_QUEUE_NAME_FORMAT = "IconScore.{channel_name}.{amqp_key}"
ICON_SERVICE_PROCTITLE_FORMAT = "icon_service." \
                                "{scoreRootPath}." \
                                "{stateDbRootPath}." \
                                "{channel}.{amqpKey}." \
                                "{amqpTarget}"


class ConfigKey:
    BUILTIN_SCORE_OWNER = 'builtinScoreOwner'
    SERVICE = 'service'
    SERVICE_FEE = 'fee'
    SERVICE_AUDIT = 'audit'
    SERVICE_DEPLOYER_WHITELIST = 'deployerWhiteList'
    SERVICE_SCORE_PACKAGE_VALIDATOR = 'scorePackageValidator'
    SCORE_ROOT_PATH = 'scoreRootPath'
    STATE_DB_ROOT_PATH = 'stateDbRootPath'
    CHANNEL = 'channel'
    AMQP_KEY = 'amqpKey'
    AMQP_TARGET = 'amqpTarget'
    CONFIG = 'config'
    TBEARS_MODE = 'tbearsMode'


class EnableThreadFlag(IntFlag):
    NonFlag = 0
    Invoke = 1
    Query = 2
    Validate = 4


class IconServiceFlag(IntFlag):
    none = 0
    fee = 1
    audit = 2
    deployerWhiteList = 4
    scorePackageValidator = 8


class IconDeployFlag(IntFlag):
    NONE = 0
    # To complete to install or update a SCORE,
    # some specified address owner like genesis address owner
    # MUST approve install or update SCORE transactions.
    ENABLE_DEPLOY_AUDIT = 1
    ENABLE_DEPLOY_WHITELIST = 2
    ENABLE_TBEARS_MODE = 4


class IconScoreLoaderFlag(IntFlag):
    NONE = 0
    ENABLE_SCORE_PACKAGE_VALIDATOR = 1


ENABLE_THREAD_FLAG = EnableThreadFlag.Invoke | EnableThreadFlag.Query | EnableThreadFlag.Validate
