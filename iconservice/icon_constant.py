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

from enum import IntFlag, unique, IntEnum, Enum, auto

GOVERNANCE_ADDRESS = "cx0000000000000000000000000000000000000001"

ICON_SERVICE_LOG_TAG = 'IconService'
ICON_EXCEPTION_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Exception'
ICON_DEPLOY_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Deploy'
ICON_LOADER_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Loader'
ICX_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Icx'
ICON_DB_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_DB'
ICON_INNER_LOG_TAG = f'IconInnerService'
IISS_LOG_TAG = "IISS"
STEP_LOG_TAG = "STEP"
WAL_LOG_TAG = "WAL"

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
    IREP = "irep"
    RREP = "rrep"

    EEP = "eep"
    IEEP = "ieep"
    REEP = "reep"

    DAPP = "dapp"
    IDAPP = "idapp"
    RDAPP = "rdapp"

    ISSUE_RESULT = "result"
    COVERED_BY_FEE = "coveredByFee"
    COVERED_BY_OVER_ISSUED_ICX = "coveredByOverIssuedICX"
    ISSUE = "issue"

    TOTAL_DELEGATION = "totalDelegation"
    VALUE = "value"

    TOTAL = "total"


ISSUE_EVENT_LOG_MAPPER = {
    IssueDataKey.PREP: {
        "event_signature": "PRepIssued(int,int,int,int)",
        "data": [IssueDataKey.IREP, IssueDataKey.RREP, IssueDataKey.TOTAL_DELEGATION,
                 IssueDataKey.VALUE]
    },
    IssueDataKey.TOTAL: {
        "event_signature": "ICXIssued(int,int,int,int)",
        "data": []
    }
}

ISSUE_CALCULATE_ORDER = [IssueDataKey.PREP]

BASE_TRANSACTION_INDEX = 0


class Revision(Enum):
    def _generate_next_value_(self, start, count, last_values):
        if self != 'LATEST':
            return start + count + 1

        return last_values[-1]

    TWO = auto()
    THREE = auto()
    FOUR = auto()
    IISS = auto()
    DECENTRALIZATION = auto()

    LATEST = auto()


RC_DB_VERSION_0 = 0
RC_DB_VERSION_2 = 2


# The case that version is updated but not revision, set the version to the current revision
# The case that both version and revision is updated, add revision field to the version table
# The case that only revision is changed, do not update this table
RC_DATA_VERSION_TABLE = {
    Revision.IISS.value: RC_DB_VERSION_0,
    Revision.DECENTRALIZATION.value: RC_DB_VERSION_2
}

IISS_DB = 'iiss'
RC_SOCKET = 'iiss.sock'

META_DB = 'meta'


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
    IISS_CALCULATE_PERIOD = "iissCalculatePeriod"
    TERM_PERIOD = 'termPeriod'
    INITIAL_IREP = 'initialIRep'
    PREP_MAIN_PREPS = 'mainPRepCount'
    PREP_MAIN_AND_SUB_PREPS = 'mainAndSubPRepCount'
    IPC_TIMEOUT = 'ipcTimeout'

    # log
    LOG = 'log'
    LOG_FILE_PATH = 'filePath'
    STEP_TRACE_FLAG = 'stepTraceFlag'

    # IISS meta data
    IISS_META_DATA = "iissMetaData"
    REWARD_POINT = 'rewardPoint'
    REWARD_MIN = "rewardMin"
    REWARD_MAX = "rewardMAX"
    UN_STAKE_LOCK_MIN = "lockMin"
    UN_STAKE_LOCK_MAX = "lockMax"

    PREP_REGISTRATION_FEE = "prepRegistrationFee"

    DECENTRALIZE_TRIGGER = "decentralizeTrigger"
    PENALTY_GRACE_PERIOD = "penaltyGracePeriod"
    LOW_PRODUCTIVITY_PENALTY_THRESHOLD = "lowProductivityPenaltyThreshold"
    BLOCK_VALIDATION_PENALTY_THRESHOLD = "blockValidationPenaltyThreshold"


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


# 0xb9eeb235f715b166cf4b91ffcf8cc48a81913896086d30104ffc0cf47eed1cbd
INVALID_CLAIM_TX = [
    b'\xb9\xee\xb25\xf7\x15\xb1f\xcfK\x91\xff\xcf\x8c\xc4\x8a\x81\x918\x96\x08m0\x10O\xfc\x0c\xf4~\xed\x1c\xbd'
]

IISS_METHOD_TABLE = [
    "setStake",
    "getStake",
    "setDelegation",
    "getDelegation",
    "claimIScore",
    "queryIScore",
    "estimateUnstakeLockPeriod"
]

PREP_METHOD_TABLE = [
    "registerPRep",
    "unregisterPRep",
    "setPRep",
    "setGovernanceVariables",
    "getPRep",
    "getMainPReps",
    "getSubPReps",
    "getPReps",
    "getPRepTerm"
]

DEBUG_METHOD_TABLE = [
    "getIISSInfo"
]

HASH_TYPE_TABLE = [
    "blockHash",
    "txHash",
    "prevBlockHash",
    "rootHash"
]

NEW_METHOD_TABLE = IISS_METHOD_TABLE + PREP_METHOD_TABLE + DEBUG_METHOD_TABLE

IISS_MAX_DELEGATIONS = 10
PREP_MAIN_PREPS = 22
PREP_MAIN_AND_SUB_PREPS = 100

IISS_MAX_REWARD_RATE = 10_000
IISS_MIN_IREP = 10_000 * ICX_IN_LOOP
IISS_MAX_IREP_PERCENTAGE = 14
IISS_INITIAL_IREP = 50_000 * ICX_IN_LOOP

# 24 hours * 60 minutes * 60 seconds / 2 - 80 <- for PRep terms
TERM_PERIOD = 24 * 60 * 60 // 2 - 80

# 24 hours * 60 minutes * 60 seconds / 2
IISS_DAY_BLOCK = 24 * 60 * 60 // 2
IISS_MONTH_BLOCK = IISS_DAY_BLOCK * 30
IISS_MONTH = 12
IISS_ANNUAL_BLOCK = IISS_MONTH_BLOCK * IISS_MONTH

PERCENTAGE_FOR_BETA_2 = 100

ISCORE_EXCHANGE_RATE = 1_000

PENALTY_GRACE_PERIOD = IISS_DAY_BLOCK * 2

LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 85     # Unit: Percent
BLOCK_VALIDATION_PENALTY_THRESHOLD = 660    # Unit: Blocks

BASE_TRANSACTION_VERSION = 3

PREP_PENALTY_SIGNATURE = "PenaltyImposed(Address,int,int)"


class RCStatus(IntEnum):
    NOT_READY = 0
    READY = 1


class RCCalculateResult(IntEnum):
    SUCCESS = 0
    FAIL = 1
    IN_PROGRESS = 2
    INVALID_BLOCK_HEIGHT = 3


class PRepStatus(Enum):
    ACTIVE = 0
    UNREGISTERED = auto()
    DISQUALIFIED = auto()


class PenaltyReason(Enum):
    NONE = 0
    # disqualified
    PREP_DISQUALIFICATION = auto()
    LOW_PRODUCTIVITY = auto()
    # suspended
    BLOCK_VALIDATION = auto()


class PRepGrade(Enum):
    MAIN = 0
    SUB = 1
    CANDIDATE = 2


class PRepResultState(Enum):
    NORMAL = 0
    IN_TERM_UPDATED = 1


class BlockVoteStatus(Enum):
    NONE = 0
    TRUE = 1
    FALSE = 2
