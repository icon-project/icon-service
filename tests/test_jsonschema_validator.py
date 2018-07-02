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

import unittest

from iconservice.base.exception import InvalidParamsException, ServerErrorException
from iconservice.base.address import AddressPrefix
from iconservice.base.jsonschema_validator import *
from tests import create_address, create_tx_hash


class TestJsonschemValidator(unittest.TestCase):
    def setUp(self):
        self.call = {
            "jsonrpc": "2.0",
            "id": 1234,
            "method": "icx_call",
            "params": {
                "from": str(create_address(AddressPrefix.EOA, b'from')),
                "to": str(create_address(AddressPrefix.EOA, b'to')),
                "dataType": "call",
                "data": {
                    "method": "get_balance",
                    "params": {
                        "address": "hx1f9a3310f60a03934b917509c86442db703cbd52"
                    }
                }
            }
        }
        self.getBalance = {
            "jsonrpc": "2.0",
            "id": 1234,
            "method": "icx_getBalance",
            "params": {
                "address": str(create_address(AddressPrefix.EOA, b'from')),
            }
        }
        self.getScoreApi = {
            "jsonrpc": "2.0",
            "id": 1234,
            "method": "icx_getScoreApi",
            "params": {
                "address": str(create_address(AddressPrefix.EOA, b'from')),
            }
        }
        self.getTotalSupply = {
            "jsonrpc": "2.0",
            "id": 1234,
            "method": "icx_getTotalSupply",
        }
        self.getTransactionResult = {
            "jsonrpc": "2.0",
            "id": 1234,
            "method": "icx_getTransactionResult",
            "params": {
                'txHash': bytes.hex(create_tx_hash(b'tx')),
            }
        }
        self.sendTransaction = {
            "jsonrpc": "2.0",
            "id": 1234,
            'method': 'icx_sendTransaction',
            'params': {
                "version": "0x3",
                "from": str(create_address(AddressPrefix.EOA, b'from')),
                "to": str(create_address(AddressPrefix.EOA, b'to')),
                "value": "0xde0b6b3a7640000",
                "stepLimit": "0x12345",
                "timestamp": "0x563a6cf330136",
                "nonce": "0x1",
                "signature": "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=",
                "dataType": "call",
                "data": {
                    "method": "transfer",
                    "params": {
                        "to": "hxab2d8215eab14bc6bdd8bfb2c8151257032ecd8b",
                        "value": "0x1"
                    }
                }
            }
        }

    def check_required(self, full_data: dict, data: dict, key: str, invalid_value: object = int(1)):
        # remove required key and test
        original_value = data.pop(key)
        self.assertRaises(InvalidParamsException, validate_jsonschema, full_data)

        # add value with invalid type. we do not support int type value
        data[key] = invalid_value
        self.assertRaises(InvalidParamsException, validate_jsonschema, full_data)

        # recover original value
        data[key] = original_value
        try:
            validate_jsonschema(full_data)
        except:
            self.fail('raise exception!')

    def test_call(self):
        try:
            validate_jsonschema(self.call)
        except:
            self.fail('raise exception!')

    def test_call_invalid_key(self):
        params = self.call['params']

        # add invalid key to params
        params['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.call)
        params.pop('invalid_key')

        # add invalid key to data
        data = params['data']
        data['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.call)
        data.pop('invalid_key')

    def test_call_required(self):
        params = self.call['params']
        self.check_required(self.call, params, 'from')
        self.check_required(self.call, params, 'to')
        self.check_required(self.call, params, 'dataType')
        self.check_required(self.call, params, 'data')

        data = self.call['params']['data']
        self.check_required(self.call, data, 'method')

    def test_getBalance(self):
        try:
            validate_jsonschema(self.getBalance)
        except:
            self.fail('raise exception!')

    def test_getBalance_invalid_key(self):
        params = self.getBalance['params']

        # add invalid key to params
        params['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.getBalance)
        params.pop('invalid_key')

    def test_getBalance_required(self):
        params = self.getBalance['params']
        self.check_required(self.getBalance, params, 'address')

    def test_getScoreApi(self):
        try:
            validate_jsonschema(self.getScoreApi)
        except:
            self.fail('raise exception!')

    def test_getScoreApi_invalid_key(self):
        params = self.getScoreApi['params']

        # add invalid key to params
        params['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.getScoreApi)
        params.pop('invalid_key')

    def test_getScoreApi_required(self):
        params = self.getScoreApi['params']
        self.check_required(self.getScoreApi, params, 'address')

    def test_getTotalSupply(self):
        try:
            validate_jsonschema(self.getTotalSupply)
        except:
            self.fail('raise exception!')

    def test_getTotalSupply_invalid_key(self):
        # add invalid key to params
        self.getTotalSupply['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.getTotalSupply)
        self.getTotalSupply.pop('invalid_key')

    def test_getTotalSupply_required(self):
        self.check_required(self.getTotalSupply, self.getTotalSupply, 'id', invalid_value="1234")

    def test_getTransactionResult(self):
        try:
            validate_jsonschema(self.getTransactionResult)
        except:
            self.fail('raise exception!')

    def test_getTransactionResult_invalid_key(self):
        params = self.getTransactionResult['params']

        # add invalid key to params
        params['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.getTransactionResult)
        params.pop('invalid_key')

    def test_getTransactionResult_required(self):
        params = self.getTransactionResult['params']
        self.check_required(self.getTransactionResult, params, 'txHash')

    def test_sendTransaction(self):
        params = self.sendTransaction['params']
        try:
            validate_jsonschema(self.sendTransaction)

            # remove non-required key and test
            params.pop('to')
            validate_jsonschema(self.sendTransaction)
        except:
            self.fail('raise exception!')

    def test_sendTransaction_invalid_key(self):
        params = self.sendTransaction['params']

        # add invalid key to params
        params['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.sendTransaction)
        params.pop('invalid_key')

        # add invalid key to data
        data = params['data']
        data['invalid_key'] = "invalid_value"
        self.assertRaises(InvalidParamsException, validate_jsonschema, self.sendTransaction)
        data.pop('invalid_key')

    def test_sendTransaction_required(self):
        params = self.sendTransaction['params']
        self.check_required(self.sendTransaction, params, 'version')
        self.check_required(self.sendTransaction, params, 'from')
        self.check_required(self.sendTransaction, params, 'stepLimit')
        self.check_required(self.sendTransaction, params, 'timestamp')
        self.check_required(self.sendTransaction, params, 'signature')

    def test_batch_request(self):
        batch_request = [self.call, self.sendTransaction, self.getTotalSupply]
        try:
            validate_jsonschema(batch_request)
        except:
            self.fail('raise exception!')
