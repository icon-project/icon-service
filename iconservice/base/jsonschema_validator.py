# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from iconservice.base.exception import InvalidParamsException, ServerErrorException

has_no_params = 0

json_request: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "json_request",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
        "params": {"type": "object"}
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id"]
}

icx_call: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_call",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_call",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string", "enum": ["icx_call"]},
        "id": {"type": "number"},
        "params": {
            "type": "object",
            "properties": {
                "from": {"type": "string", "maxLength": 42},
                "to": {"type": "string", "maxLength": 42},
                "dataType": {"type": "string", "enum": ["call"]},
                "data": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "params": {"type": "object"}
                    },
                    "additionalProperties": False,
                    "required": ["method"]
                },
            },
            "additionalProperties": False,
            "required": ["from", "to", "dataType", "data"]
        }
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id", "params"]
}

icx_getBalance: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_getBalance",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_getbalance",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
        "params": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "maxLength": 42},
            },
            "additionalProperties": False,
            "required": ["address"]
        }
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id", "params"]
}

icx_getScoreApi: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_getScoreApi",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_getscoreapi",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
        "params": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "maxLength": 42},
            },
            "additionalProperties": False,
            "required": ["address"]
        }
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id", "params"]
}

icx_getTotalSupply: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_getBalance",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_gettotalsupply",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id"]
}

icx_getTransactionResult: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_getTransactionResult",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_gettransactionresult",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
        "params": {
            "type": "object",
            "properties": {
                "txHash": {"type": "string"}
            },
            "additionalProperties": False,
            "required": ["txHash"]
        }
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id", "params"]
}

icx_sendTransaction: dict = {
    "$schema": "http://json-schema.org/schema#",
    "title": "icx_sendTransaction",
    "id": "https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3#icx_sendtransaction",
    "type": "object",
    "properties": {
        "jsonrpc": {"type": "string", "enum": ["2.0"]},
        "method": {"type": "string"},
        "id": {"type": "number"},
        "params": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "from": {"type": "string", "maxLength": 42},
                "to": {"type": "string", "maxLength": 42},
                "value": {"type": "string"},
                "stepLimit": {"type": "string"},
                "timestamp": {"type": "string"},
                "nonce": {"type": "string"},
                "signature": {"type": "string"},
                "dataType": {"type": "string", "enum": ["call", "deploy"]},
                "data": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "contentType": {"type": "string"},
                        "content": {"type": "string"},
                        "params": {"type": "object"}
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
            "required": ["version", "from", "stepLimit", "timestamp", "signature"]
        }
    },
    "additionalProperties": False,
    "required": ["jsonrpc", "method", "id", "params"]

}

SCHEMA: dict = {
    "icx_call": icx_call,
    "icx_getBalance": icx_getBalance,
    "icx_getScoreApi": icx_getScoreApi,
    "icx_getTotalSupply": icx_getTotalSupply,
    "icx_getTransactionResult": icx_getTransactionResult,
    "icx_sendTransaction": icx_sendTransaction
}


def validate_jsonschema(request: object):
    """ Validate JSON-RPC v3 schema.

    refer to https://repo.theloop.co.kr/theloop/LoopChain/wikis/doc/loopchain-json-rpc-v3

    :param request: JSON-RPC request
    :return: N/A
    """
    # get JSON-RPC batch request
    if isinstance(request, list):
        for req in request:
            validate_jsonschema(req)
        return

    # get schema for 'method'
    schema = SCHEMA.get(request['method'], None)
    if schema is None:
        raise ServerErrorException(message=f"Method '{request['method']}' is not supported'")

    # check request
    try:
        validate(instance=request, schema=schema)
    except ValidationError as e:
        raise InvalidParamsException(message=f"JSON schema validation error: {e}")
