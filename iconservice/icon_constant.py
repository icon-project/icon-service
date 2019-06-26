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

from enum import IntFlag, unique, IntEnum, Enum

GOVERNANCE_ADDRESS = "cx0000000000000000000000000000000000000001"

ICON_SERVICE_LOG_TAG = 'IconService'
ICON_EXCEPTION_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Exception'
ICON_DEPLOY_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Deploy'
ICON_LOADER_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Loader'
ICX_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Icx'
ICON_DB_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_DB'
ICON_INNER_LOG_TAG = f'IconInnerService'

JSONRPC_VERSION = '2.0'
CHARSET_ENCODING = 'utf-8'

ICX_IN_LOOP = 10 ** 18
# 32bytes == 256bit
DEFAULT_BYTE_SIZE = 32
DATA_BYTE_ORDER = 'big'  # big endian
# Fixed fee is 0.01 icx.
FIXED_FEE = 10 ** 16
# Max data field size
MAX_DATA_SIZE = 512 * 1024

# Max external call count(1 is default SCORE call, 1024 is external call in the SCORE)
MAX_EXTERNAL_CALL_COUNT = 1 + 1024

# Max call stack size
MAX_CALL_STACK_SIZE = 64

ICON_DEX_DB_NAME = 'icon_dex'
PACKAGE_JSON_FILE = 'package.json'

ICX_TRANSFER_EVENT_LOG = 'ICXTransfer(Address,Address,int)'

ICON_SCORE_QUEUE_NAME_FORMAT = "IconScore.{channel_name}.{amqp_key}"
ICON_SERVICE_PROCTITLE_FORMAT = "icon_service." \
                                "{scoreRootPath}." \
                                "{stateDbRootPath}." \
                                "{channel}.{amqpKey}." \
                                "{amqpTarget}"

BUILTIN_SCORE_ADDRESS_MAPPER = {'governance': GOVERNANCE_ADDRESS}

ZERO_TX_HASH = bytes(32)


class IssueDataKey:
    PREP = "prep"
    TOTAL = "total"

    IREP = "irep"
    RREP = "rrep"
    TOTAL_DELEGATION = "totalDelegation"
    VALUE = "value"


ISSUE_EVENT_LOG_MAPPER = {
    IssueDataKey.PREP: {
        "indexed": ["PRepIssued(int,int,int,int)"],
        "data": [IssueDataKey.IREP, IssueDataKey.RREP, IssueDataKey.TOTAL_DELEGATION,
                 IssueDataKey.VALUE]
    },
    IssueDataKey.TOTAL: {
        "indexed": ["ICXIssued(int,int,int,int)"],
        "data": []
    }
}

ISSUE_CALCULATE_ORDER = [IssueDataKey.PREP]

ICX_ISSUE_TRANSACTION_INDEX = 0

REVISION_2 = 2
REVISION_3 = 3
REVISION_4 = 4
REVISION_5 = 5

LATEST_REVISION = REVISION_4

REV_IISS = REVISION_5 + 1
REV_DECENTRALIZATION = REV_IISS + 1

IISS_DB = 'iiss'


class ConfigKey:
    BUILTIN_SCORE_OWNER = 'builtinScoreOwner'
    SERVICE = 'service'
    SERVICE_FEE = 'fee'
    SERVICE_AUDIT = 'audit'
    SERVICE_DEPLOYER_WHITE_LIST = 'deployerWhiteList'
    SERVICE_SCORE_PACKAGE_VALIDATOR = 'scorePackageValidator'
    SCORE_ROOT_PATH = 'scoreRootPath'
    STATE_DB_ROOT_PATH = 'stateDbRootPath'
    CHANNEL = 'channel'
    AMQP_KEY = 'amqpKey'
    AMQP_TARGET = 'amqpTarget'
    CONFIG = 'config'
    TBEARS_MODE = 'tbearsMode'
    IISS_UNSTAKE_LOCK_PERIOD = "iissUnstakeLockPeriod"
    IISS_PREP_LIST = "iissPRepList"
    IISS_CALCULATE_PERIOD = "iissCalculatePeriod"
    TERM_PERIOD = 'termPeriod'
    IREP = 'irep'

    # IISS VARIABLE
    IISS_REWARD_VARIABLE = "iissRewardVariable"
    IISS_INITIAL_IREP = "iissInitialIRep"
    REWARD_POINT = 'rewardPoint'
    REWARD_MIN = "rewardMin"
    REWARD_MAX = "rewardMAX"


class EnableThreadFlag(IntFlag):
    INVOKE = 1
    QUERY = 2
    VALIDATE = 4


class IconServiceFlag(IntFlag):
    FEE = 1
    AUDIT = 2
    DEPLOYER_WHITE_LIST = 4
    SCORE_PACKAGE_VALIDATOR = 8


@unique
class IconScoreContextType(IntEnum):
    # Write data to db directly
    DIRECT = 0
    # Record data to cache and after confirming the block, write them to db
    INVOKE = 1
    # Record data to cache for estimation of steps, discard cache after estimation.
    ESTIMATION = 2
    # Not possible to write data to db
    QUERY = 3


@unique
class IconScoreFuncType(IntEnum):
    # ReadOnly function
    READONLY = 0
    # Writable function
    WRITABLE = 1


ENABLE_THREAD_FLAG = EnableThreadFlag.INVOKE | EnableThreadFlag.QUERY | EnableThreadFlag.VALIDATE


class DeployType(IntEnum):
    INSTALL = 0
    UPDATE = 1


class DeployState(IntEnum):
    INACTIVE = 0
    ACTIVE = 1


IISS_METHOD_TABLE = [
    "setStake",
    "getStake",
    "setDelegation",
    "getDelegation",
    "claimIScore",
    "queryIScore",
]

PREP_METHOD_TABLE = [
    "registerPRep",
    "unregisterPRep",
    "setPRep",
    "getPRep",
    "getMainPRepList",
    "getSubPRepList",
    "getPRepList"
]

NEW_METHOD_TABLE = IISS_METHOD_TABLE + PREP_METHOD_TABLE

IISS_MAX_DELEGATIONS = 10
PREP_SUB_PREPS = 100
PREP_MAIN_PREPS = 22

IISS_MAX_REWARD_RATE = 10_000
IISS_MIN_IREP = 10_000
IISS_INITIAL_IREP = 37_500
IISS_SOCKET_PATH = "/tmp/iiss.sock"

IISS_ANNUAL_BLOCK = 15_768_000
IISS_MONTH = 12

ISCORE_EXCHANGE_RATE = 1_000

PENALTY_GRACE_PERIOD = 86_240

MIN_PRODUCTIVITY_PERCENTAGE = 85

ISSUE_TRANSACTION_VERSION = 3


class PRepStatus(Enum):
    NONE = 0
    ACTIVE = 1
    UNREGISTERED = 2
    PENALTY1 = 3
    PENALTY2 = 4


PREP_STATUS_MAPPER = {
    PRepStatus.ACTIVE: "active",
    PRepStatus.UNREGISTERED: "unregistered",
    PRepStatus.PENALTY1: "prep disqualification penalty",
    PRepStatus.PENALTY2: "low productivity penalty"
}


class PrepResultState(Enum):
    NORMAL = 0
    PENALTY = 1
