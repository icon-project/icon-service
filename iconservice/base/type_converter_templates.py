# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import IntEnum


class ParamType(IntEnum):
    BLOCK = 0

    INVOKE_TRANSACTION = 100
    ACCOUNT_DATA = 101
    CALL_DATA = 102
    DEPLOY_DATA = 103
    TRANSACTION_PARAMS_DATA = 104
    DEPOSIT_DATA = 105

    INVOKE = 200

    QUERY = 300
    ICX_CALL = 301
    ICX_GET_BALANCE = 302
    ICX_GET_TOTAL_SUPPLY = 303
    ICX_GET_SCORE_API = 304
    ISE_GET_STATUS = 305

    WRITE_PRECOMMIT = 400
    REMOVE_PRECOMMIT = 500

    VALIDATE_TRANSACTION = 600

    # IISS
    IISS = 700
    IISS_SET_STAKE = 701
    IISS_GET_STAKE = 702
    IISS_SET_DELEGATION = 703
    IISS_GET_DELEGATION = 704
    IISS_CLAIM_I_SCORE = 705
    IISS_QUERY_I_SCORE = 706
    IISS_REG_PREP_CANDIDATE = 707
    IISS_UNREG_PREP_CANDIDATE = 708
    IISS_SET_PREP_CANDIDATE = 709
    IISS_GET_PREP_CANDIDATE = 710
    IISS_GET_PREP_CANDIDATE_DELEGATION_INFO = 711
    IISS_GET_PREP_LIST = 712
    IISS_GET_PREP_CANDIDATE_LIST = 713


class ValueType(IntEnum):
    IGNORE = 0
    LATER = 1
    INT = 2
    STRING = 3
    BOOL = 4
    ADDRESS = 5
    BYTES = 6

    # For backward compatibility (TestNet)
    ADDRESS_OR_MALFORMED_ADDRESS = 7
    HEXADECIMAL = 8


type_convert_templates = {}
CONVERT_USING_SWITCH_KEY = 'CONVERT_USING_SWITCH_KEY'
SWITCH_KEY = "SWITCH_KEY"
KEY_CONVERTER = 'KEY_CONVERTER'


class ConstantKeys:
    BLOCK_HEIGHT = "blockHeight"
    BLOCK_HASH = "blockHash"
    OLD_BLOCK_HASH = "oldBlockHash"
    NEW_BLOCK_HASH = "newBlockHash"
    TIMESTAMP = "timestamp"
    PREV_BLOCK_HASH = "prevBlockHash"

    NAME = "name"
    ADDRESS = "address"
    BALANCE = "balance"

    METHOD = "method"
    PARAMS = "params"

    CONTENT_TYPE = "contentType"
    CONTENT = "content"

    TX_HASH = "txHash"
    VERSION = "version"
    FROM = "from"
    TO = "to"
    VALUE = "value"
    STEP_LIMIT = "stepLimit"
    FEE = "fee"
    NONCE = "nonce"
    SIGNATURE = "signature"

    DATA_TYPE = "dataType"
    DATA = "data"
    CALL = "call"
    DEPLOY = "deploy"

    OLD_TX_HASH = "tx_hash"

    GENESIS_DATA = "genesisData"
    ACCOUNTS = "accounts"
    MESSAGE = "message"

    BLOCK = "block"
    TRANSACTIONS = "transactions"

    FILTER = "filter"

    ICX_CALL = "icx_call"
    ICX_GET_BALANCE = "icx_getBalance"
    ICX_GET_TOTAL_SUPPLY = "icx_getTotalSupply"
    ICX_GET_SCORE_API = "icx_getScoreApi"
    ISE_GET_STATUS = "ise_getStatus"

    DEPOSIT_TERM = "term"
    DEPOSIT_ID = "id"

    # IISS
    DELEGATIONS = "delegations"
    NETWORK_INFO = "networkInfo"
    URL = 'url'
    GOVERNANCE = "governance"
    ICX_PRICE = "icxPrice"
    INCENTIVE_REP = "incentiveRep"
    START_RANK = "startRank"
    END_RANK = "endRank"


type_convert_templates[ParamType.BLOCK] = {
    ConstantKeys.BLOCK_HEIGHT: ValueType.INT,
    ConstantKeys.BLOCK_HASH: ValueType.BYTES,
    ConstantKeys.TIMESTAMP: ValueType.INT,
    ConstantKeys.PREV_BLOCK_HASH: ValueType.BYTES,
}

type_convert_templates[ParamType.ACCOUNT_DATA] = {
    ConstantKeys.NAME: ValueType.STRING,
    ConstantKeys.ADDRESS: ValueType.ADDRESS,
    ConstantKeys.BALANCE: ValueType.INT
}

type_convert_templates[ParamType.CALL_DATA] = {
    ConstantKeys.METHOD: ValueType.STRING,
    ConstantKeys.PARAMS: ValueType.LATER
}

type_convert_templates[ParamType.DEPLOY_DATA] = {
    ConstantKeys.CONTENT_TYPE: ValueType.STRING,
    ConstantKeys.CONTENT: ValueType.IGNORE,
    ConstantKeys.PARAMS: ValueType.LATER
}

type_convert_templates[ParamType.TRANSACTION_PARAMS_DATA] = {
    ConstantKeys.VERSION: ValueType.INT,
    ConstantKeys.TX_HASH: ValueType.BYTES,
    ConstantKeys.FROM: ValueType.ADDRESS,
    ConstantKeys.TO: ValueType.ADDRESS_OR_MALFORMED_ADDRESS,
    ConstantKeys.VALUE: ValueType.HEXADECIMAL,
    ConstantKeys.STEP_LIMIT: ValueType.INT,
    ConstantKeys.FEE: ValueType.HEXADECIMAL,
    ConstantKeys.TIMESTAMP: ValueType.INT,
    ConstantKeys.NONCE: ValueType.INT,
    ConstantKeys.SIGNATURE: ValueType.IGNORE,
    ConstantKeys.DATA_TYPE: ValueType.STRING,
    ConstantKeys.DATA: {
        CONVERT_USING_SWITCH_KEY: {
            SWITCH_KEY: ConstantKeys.DATA_TYPE,
            ConstantKeys.CALL: type_convert_templates[ParamType.CALL_DATA],
            ConstantKeys.DEPLOY: type_convert_templates[ParamType.DEPLOY_DATA]
        }
    },
    KEY_CONVERTER: {
        ConstantKeys.OLD_TX_HASH: ConstantKeys.TX_HASH
    }
}

type_convert_templates[ParamType.INVOKE_TRANSACTION] = {
    ConstantKeys.METHOD: ValueType.STRING,
    ConstantKeys.PARAMS: type_convert_templates[ParamType.TRANSACTION_PARAMS_DATA],
    ConstantKeys.GENESIS_DATA: {
        ConstantKeys.ACCOUNTS: [
            type_convert_templates[ParamType.ACCOUNT_DATA]
        ],
        ConstantKeys.MESSAGE: ValueType.STRING
    }
}

type_convert_templates[ParamType.INVOKE] = {
    ConstantKeys.BLOCK: type_convert_templates[ParamType.BLOCK],
    ConstantKeys.TRANSACTIONS: [
        type_convert_templates[ParamType.INVOKE_TRANSACTION]
    ]
}

type_convert_templates[ParamType.ICX_CALL] = {
    ConstantKeys.VERSION: ValueType.INT,
    ConstantKeys.FROM: ValueType.ADDRESS,
    ConstantKeys.TO: ValueType.ADDRESS,
    ConstantKeys.DATA_TYPE: ValueType.STRING,
    ConstantKeys.DATA: ValueType.LATER
}
type_convert_templates[ParamType.ICX_GET_BALANCE] = {
    ConstantKeys.VERSION: ValueType.INT,
    ConstantKeys.ADDRESS: ValueType.ADDRESS_OR_MALFORMED_ADDRESS
}
type_convert_templates[ParamType.ICX_GET_TOTAL_SUPPLY] = {
    ConstantKeys.VERSION: ValueType.INT
}
type_convert_templates[ParamType.ICX_GET_SCORE_API] = type_convert_templates[ParamType.ICX_GET_BALANCE]

type_convert_templates[ParamType.ISE_GET_STATUS] = {
    ConstantKeys.FILTER: [ValueType.STRING]
}

type_convert_templates[ParamType.QUERY] = {
    ConstantKeys.METHOD: ValueType.STRING,
    ConstantKeys.PARAMS: {
        CONVERT_USING_SWITCH_KEY: {
            SWITCH_KEY: ConstantKeys.METHOD,
            ConstantKeys.ICX_CALL: type_convert_templates[ParamType.ICX_CALL],
            ConstantKeys.ICX_GET_BALANCE: type_convert_templates[ParamType.ICX_GET_BALANCE],
            ConstantKeys.ICX_GET_TOTAL_SUPPLY: type_convert_templates[ParamType.ICX_GET_TOTAL_SUPPLY],
            ConstantKeys.ICX_GET_SCORE_API: type_convert_templates[ParamType.ICX_GET_SCORE_API],
            ConstantKeys.ISE_GET_STATUS: type_convert_templates[ParamType.ISE_GET_STATUS]
        }
    }
}

type_convert_templates[ParamType.WRITE_PRECOMMIT] = {
    ConstantKeys.BLOCK_HEIGHT: ValueType.INT,
    ConstantKeys.BLOCK_HASH: ValueType.BYTES,
    ConstantKeys.OLD_BLOCK_HASH: ValueType.BYTES,
    ConstantKeys.NEW_BLOCK_HASH: ValueType.BYTES
}

type_convert_templates[ParamType.REMOVE_PRECOMMIT] = type_convert_templates[ParamType.WRITE_PRECOMMIT]

type_convert_templates[ParamType.VALIDATE_TRANSACTION] = {
    ConstantKeys.METHOD: ValueType.STRING,
    ConstantKeys.PARAMS: type_convert_templates[ParamType.TRANSACTION_PARAMS_DATA]
}

# DEPOSIT
type_convert_templates[ParamType.DEPOSIT_DATA] = {
    ConstantKeys.DEPOSIT_ID: ValueType.BYTES,
    ConstantKeys.DEPOSIT_TERM: ValueType.INT,
}

# IISS
type_convert_templates[ParamType.IISS_SET_STAKE] = {
    ConstantKeys.VALUE: ValueType.INT
}

type_convert_templates[ParamType.IISS_GET_STAKE] = {
    ConstantKeys.ADDRESS: ValueType.ADDRESS
}

type_convert_templates[ParamType.IISS_SET_DELEGATION] = {
    ConstantKeys.DELEGATIONS: [{
        ConstantKeys.ADDRESS: ValueType.ADDRESS,
        ConstantKeys.VALUE: ValueType.INT
    }]
}

type_convert_templates[ParamType.IISS_GET_DELEGATION] = type_convert_templates[ParamType.IISS_GET_STAKE]

type_convert_templates[ParamType.IISS_CLAIM_I_SCORE] = {}

type_convert_templates[ParamType.IISS_QUERY_I_SCORE] = type_convert_templates[ParamType.IISS_GET_STAKE]

type_convert_templates[ParamType.IISS_REG_PREP_CANDIDATE] = {
    ConstantKeys.NETWORK_INFO: ValueType.STRING,
    ConstantKeys.NAME: ValueType.STRING,
    ConstantKeys.URL: ValueType.STRING,
    ConstantKeys.GOVERNANCE: {
        ConstantKeys.ICX_PRICE: ValueType.INT,
        ConstantKeys.INCENTIVE_REP: ValueType.INT
    }
}

type_convert_templates[ParamType.IISS_UNREG_PREP_CANDIDATE] = type_convert_templates[ParamType.IISS_CLAIM_I_SCORE]

type_convert_templates[ParamType.IISS_SET_PREP_CANDIDATE] = type_convert_templates[ParamType.IISS_REG_PREP_CANDIDATE]

type_convert_templates[ParamType.IISS_GET_PREP_CANDIDATE] = type_convert_templates[ParamType.IISS_GET_STAKE]

type_convert_templates[ParamType.IISS_GET_PREP_CANDIDATE_DELEGATION_INFO] = \
    type_convert_templates[ParamType.IISS_GET_STAKE]

type_convert_templates[ParamType.IISS_GET_PREP_LIST] = type_convert_templates[ParamType.IISS_CLAIM_I_SCORE]

type_convert_templates[ParamType.IISS_GET_PREP_CANDIDATE_LIST] = {
    ConstantKeys.START_RANK: ValueType.INT,
    ConstantKeys.END_RANK: ValueType.INT
}
