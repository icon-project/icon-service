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

from enum import IntFlag, unique, IntEnum, Enum, auto, Flag

SYSTEM_ADDRESS = "cx0000000000000000000000000000000000000000"
GOVERNANCE_ADDRESS = "cx0000000000000000000000000000000000000001"

ICON_DEPLOY_LOG_TAG = "DEPLOY"
ICON_LOADER_LOG_TAG = "LOADER"
ICX_LOG_TAG = "ICX"
ICON_DB_LOG_TAG = "DB"
IISS_LOG_TAG = "IISS"
STEP_LOG_TAG = "STEP"
WAL_LOG_TAG = "WAL"
ROLLBACK_LOG_TAG = "ROLLBACK"
BACKUP_LOG_TAG = "BACKUP"

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

BUILTIN_SCORE_ADDRESS_MAPPER = {
    'governance': GOVERNANCE_ADDRESS,
    'system': SYSTEM_ADDRESS
}
BUILTIN_SCORE_IMPORT_WHITE_LIST = {"iconservice.iconscore.system": "['*']"}

ZERO_TX_HASH = bytes(DEFAULT_BYTE_SIZE)


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
    GENESIS = 0
    TWO = 2
    THREE = 3
    FOUR = 4
    IISS = 5
    DECENTRALIZATION = 6
    FIX_TOTAL_ELECTED_PREP_DELEGATED = 7

    # Revision 8
    REALTIME_P2P_ENDPOINT_UPDATE = 8
    OPTIMIZE_DIRTY_PREP_UPDATE = 8

    # Revision 9
    FIX_EMAIL_VALIDATION = 9
    DIVIDE_NODE_ADDRESS = 9
    FIX_BURN_EVENT_SIGNATURE = 9
    ADD_LOGS_BLOOM_ON_BASE_TX = 9
    SCORE_FUNC_PARAMS_CHECK = 9
    SYSTEM_SCORE_ENABLED = 9
    CHANGE_MAX_DELEGATIONS_TO_100 = 9
    PREVENT_DUPLICATED_ENDPOINT = 9
    SET_IREP_VIA_NETWORK_PROPOSAL = 9
    MULTIPLE_UNSTAKE = 9
    FIX_COIN_PART_BYTES_ENCODING = 9
    STRICT_SCORE_DECORATOR_CHECK = 9

    FIX_UNSTAKE_BUG = 10
    LOCK_ADDRESS = 10

    FIX_BALANCE_BUG = 11

    BURN_V2_ENABLED = 12
    IMPROVED_PRE_VALIDATOR = 12
    VERIFY_ASSET_INTEGRITY = 12
    USE_RLP = 12

    LATEST = 12


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
    LOGGER = "logger"
    LOG_FILE_PATH = 'filePath'
    LOG_LEVEL = "level"
    LOG_OUTPUT_TYPE = "outputType"
    LOG_ROTATE = "rotate"
    LOG_ROTATE_TYPE = "type"
    LOG_ROTATE_PERIOD = "period"
    LOG_ROTATE_INTERVAL = "interval"
    LOG_ROTATE_AT_TIME = "atTime"
    LOG_ROTATE_MAX_BYTES = "maxBytes"
    LOG_ROTATE_BACKUP_COUNT = "backupCount"
    STEP_TRACE_FLAG = 'stepTraceFlag'
    PRECOMMIT_DATA_LOG_FLAG = 'precommitDataLogFlag'

    # Reward calculator
    # executable path
    ICON_RC_DIR_PATH = 'iconRcPath'
    # Boolean which determines Opening RC monitor channel (Default True)
    ICON_RC_MONITOR = 'iconRcMonitor'

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

    # The maximum number of backup files for rollback
    BACKUP_FILES = "backupFiles"

    # Block invoke timeout in second
    BLOCK_INVOKE_TIMEOUT = "blockInvokeTimeout"

    UNSTAKE_SLOT_MAX = "unstakeSlotMax"

    # The list of items(address, unstake, unstake_block_height)
    # containing invalid expired unstakes to remove
    INVALID_EXPIRED_UNSTAKES_PATH = "invalidExpiredUnstakesPath"


class EnableThreadFlag(IntFlag):
    INVOKE = 1
    QUERY = 2
    VALIDATE = 4


class IconServiceFlag(IntFlag):
    FEE = 1
    AUDIT = 2
    # DEPLOYER_WHITE_LIST = 4
    SCORE_PACKAGE_VALIDATOR = 8


class IconNetworkValueType(Enum):
    SERVICE_CONFIG = b'service_config'

    STEP_PRICE = b'step_price'
    STEP_COSTS = b'step_costs'
    MAX_STEP_LIMITS = b'max_step_limits'

    REVISION_CODE = b'revision_code'
    REVISION_NAME = b'revision_name'

    SCORE_BLACK_LIST = b'score_black_list'
    IMPORT_WHITE_LIST = b'import_white_list'

    IREP = b'irep'

    @classmethod
    def gs_migration_type_list(cls) -> list:
        return [
            cls.SERVICE_CONFIG,
            cls.STEP_PRICE,
            cls.STEP_COSTS,
            cls.MAX_STEP_LIMITS,
            cls.REVISION_CODE,
            cls.REVISION_NAME,
            cls.SCORE_BLACK_LIST,
            cls.IMPORT_WHITE_LIST,
        ]

    @classmethod
    def gs_migration_count(cls) -> int:
        return len(cls.gs_migration_type_list())


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

HASH_TYPE_TABLE = [
    "blockHash",
    "txHash",
    "prevBlockHash",
    "rootHash"
]

PREP_MAIN_PREPS = 22
PREP_MAIN_AND_SUB_PREPS = 100
PREP_REGISTRATION_FEE = 2_000 * ICX_IN_LOOP

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

UNSTAKE_SLOT_MAX = 1_000

PERCENTAGE_FOR_BETA_2 = 100

ISCORE_EXCHANGE_RATE = 1_000

PENALTY_GRACE_PERIOD = IISS_DAY_BLOCK * 2

LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 85  # Unit: Percent
BLOCK_VALIDATION_PENALTY_THRESHOLD = 660  # Unit: Blocks

BASE_TRANSACTION_VERSION = 3

PREP_PENALTY_SIGNATURE = "PenaltyImposed(Address,int,int)"

BACKUP_FILES = 10

BLOCK_INVOKE_TIMEOUT_S = 15


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


class PRepFlag(Flag):
    """Setting flags to True means that PRep fields specified by the flags has been changed

    """
    NONE = 0
    STATUS = auto()
    NAME = auto()
    COUNTRY = auto()
    CITY = auto()
    EMAIL = auto()
    WEBSITE = auto()
    DETAILS = auto()
    P2P_ENDPOINT = auto()
    PENALTY = auto()
    GRADE = auto()
    STAKE = auto()
    DELEGATED = auto()
    LAST_GENERATE_BLOCK_HEIGHT = auto()
    TOTAL_BLOCKS = auto()
    VALIDATED_BLOCKS = auto()
    UNVALIDATED_SEQUENCE_BLOCKS = auto()
    IREP = auto()  # irep, irep_block_height
    IREP_BLOCK_HEIGHT = auto()
    NODE_ADDRESS = auto()

    BLOCK_STATISTICS = TOTAL_BLOCKS | VALIDATED_BLOCKS | UNVALIDATED_SEQUENCE_BLOCKS
    ALL = 0xFFFFFFFF


class PRepContainerFlag(Flag):
    NONE = 0
    DIRTY = auto()


class TermFlag(Flag):
    NONE = 0
    MAIN_PREPS = auto()
    SUB_PREPS = auto()
    MAIN_PREP_P2P_ENDPOINT = auto()
    MAIN_PREP_NODE_ADDRESS = auto()

    ALL = 0xFFFFFFFF


class RevisionChangedFlag(Flag):
    # Empty
    NONE = 0x0
    # Set when STEP price changed on the block
    # STEP_PRICE_CHANGED = 0x10
    # Set when STEP costs changed on the block
    # STEP_COST_CHANGED = 0x20
    # Set when Max STEP limits changed on the block
    # STEP_MAX_LIMIT_CHANGED = 0x40
    # STEP changed flag mask
    # STEP_ALL_CHANGED = 0xf0

    # CHANGE REVISION
    GENESIS_IISS_CALC = 0x100
    IISS_CALC = 0x200
    DECENTRALIZATION = 0x400


class RPCMethod:
    ICX_GET_BALANCE = 'icx_getBalance'
    ICX_GET_TOTAL_SUPPLY = 'icx_getTotalSupply'
    ICX_GET_SCORE_API = 'icx_getScoreApi'
    ISE_GET_STATUS = 'ise_getStatus'
    ICX_CALL = 'icx_call'
    ICX_SEND_TRANSACTION = 'icx_sendTransaction'
    DEBUG_ESTIMATE_STEP = "debug_estimateStep"
    DEBUG_GET_ACCOUNT = "debug_getAccount"


class DataType:
    CALL = "call"
    DEPLOY = "deploy"
    DEPOSIT = "deposit"
    MESSAGE = "message"
    NONE = None

    _TYPES = {CALL, DEPLOY, DEPOSIT, MESSAGE, NONE}

    @classmethod
    def contains(cls, value: str) -> bool:
        return value in cls._TYPES
