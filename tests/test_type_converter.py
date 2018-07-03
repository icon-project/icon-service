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

from iconservice.base.address import AddressPrefix
from iconservice.base.type_converter import TypeConverter, ParamType
from tests import create_block_hash, create_address


class TestTypeConverter(unittest.TestCase):

    def test_block_convert(self):
        block_height = 1001
        block_hash = create_block_hash(b'block1')
        timestamp = 12345
        prev_block_hash = create_block_hash(b'prevBlock1')

        request_params = {
            "blockHeight": hex(block_height),
            "blockHash": bytes.hex(block_hash),
            "timestamp": hex(timestamp),
            "prevBlockHash": bytes.hex(prev_block_hash)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.BLOCK)

        self.assertEqual(block_height, ret_params['blockHeight'])
        self.assertEqual(block_hash, ret_params['blockHash'])
        self.assertEqual(timestamp, ret_params['timestamp'])
        self.assertEqual(prev_block_hash, ret_params['prevBlockHash'])

    def test_account_convert(self):
        name = 'genesis'
        address = create_address(AddressPrefix.EOA, b'addr')
        balance = 10000 * 10 ** 18

        request_params = {
            "name": name,
            "address": str(address),
            "balance": hex(balance),
        }

        ret_params = TypeConverter.convert(request_params, ParamType.ACCOUNT_DATA)

        self.assertEqual(name, ret_params['name'])
        self.assertEqual(address, ret_params['address'])
        self.assertEqual(balance, ret_params['balance'])

    def test_call_data_convert(self):
        method = 'method'
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "method": method,
            "params":
                {
                    "from": str(data_from),
                    "to": str(data_to),
                    "value": hex(data_value)
                }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.CALL_DATA)

        self.assertEqual(method, ret_params['method'])
        self.assertNotEqual(data_from, ret_params['params']['from'])
        self.assertNotEqual(data_to, ret_params['params']['to'])
        self.assertNotEqual(data_value, ret_params['params']['value'])

    def test_deploy_data_convert(self):
        content_type = 'application/zip'
        content = "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e"
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "contentType": content_type,
            "content": content,
            "params":
                {
                    "from": str(data_from),
                    "to": str(data_to),
                    "value": hex(data_value)
                }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.DEPLOY_DATA)

        self.assertEqual(content_type, ret_params['contentType'])
        self.assertEqual(content, ret_params['content'])
        self.assertNotEqual(data_from, ret_params['params']['from'])
        self.assertNotEqual(data_to, ret_params['params']['to'])
        self.assertNotEqual(data_value, ret_params['params']['value'])

    def test_transaction_convert1(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash(b'txHash')
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        value = 10 * 10 ** 18
        step_limit = 1000
        timestamp = 12345
        nonce = 123
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
        data_type = "call"
        data_method = "transfer"
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "method": method,
            "params": {
                "txHash": bytes.hex(tx_hash),
                "version": hex(version),
                "from": str(from_addr),
                "to": str(to_addr),
                "value": hex(value),
                "stepLimit": hex(step_limit),
                "timestamp": hex(timestamp),
                "nonce": hex(nonce),
                "signature": signature,
                "dataType": data_type,
                "data": {
                    "method": data_method,
                    "params": {
                        "from": str(data_from),
                        "to": str(data_to),
                        "value": hex(data_value)
                    }
                }
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.TRANSACTION)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(tx_hash, ret_params['params']['txHash'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(from_addr, ret_params['params']['from'])
        self.assertEqual(to_addr, ret_params['params']['to'])
        self.assertEqual(value, ret_params['params']['value'])
        self.assertEqual(step_limit, ret_params['params']['stepLimit'])
        self.assertEqual(timestamp, ret_params['params']['timestamp'])
        self.assertEqual(nonce, ret_params['params']['nonce'])
        self.assertEqual(signature, ret_params['params']['signature'])
        self.assertEqual(data_type, ret_params['params']['dataType'])
        self.assertEqual(data_method, ret_params['params']['data']['method'])
        self.assertNotEqual(data_from, ret_params['params']['data']['params']['from'])
        self.assertNotEqual(data_to, ret_params['params']['data']['params']['to'])
        self.assertNotEqual(data_value, ret_params['params']['data']['params']['value'])

    def test_transaction_conver2(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash(b'txHash')
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        value = 10 * 10 ** 18
        step_limit = 1000
        timestamp = 12345
        nonce = 123
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
        data_type = "deploy"
        content_type = "application/zip"
        content = "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e"
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "method": method,
            "params": {
                "txHash": bytes.hex(tx_hash),
                "version": hex(version),
                "from": str(from_addr),
                "to": str(to_addr),
                "value": hex(value),
                "stepLimit": hex(step_limit),
                "timestamp": hex(timestamp),
                "nonce": hex(nonce),
                "signature": signature,
                "dataType": data_type,
                "data": {
                    "contentType": content_type,
                    "content": content,
                    "params": {
                        "from": str(data_from),
                        "to": str(data_to),
                        "value": hex(data_value)
                    }
                }
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.TRANSACTION)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(tx_hash, ret_params['params']['txHash'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(from_addr, ret_params['params']['from'])
        self.assertEqual(to_addr, ret_params['params']['to'])
        self.assertEqual(value, ret_params['params']['value'])
        self.assertEqual(step_limit, ret_params['params']['stepLimit'])
        self.assertEqual(timestamp, ret_params['params']['timestamp'])
        self.assertEqual(nonce, ret_params['params']['nonce'])
        self.assertEqual(signature, ret_params['params']['signature'])
        self.assertEqual(data_type, ret_params['params']['dataType'])
        self.assertEqual(content_type, ret_params['params']['data']['contentType'])
        self.assertEqual(content, ret_params['params']['data']['content'])
        self.assertNotEqual(data_from, ret_params['params']['data']['params']['from'])
        self.assertNotEqual(data_to, ret_params['params']['data']['params']['to'])
        self.assertNotEqual(data_value, ret_params['params']['data']['params']['value'])

    def test_invoke_convert(self):
        block_height = 1001
        block_hash = create_block_hash(b'block1')
        timestamp = 12345
        prev_block_hash = create_block_hash(b'prevBlock1')

        method = "icx_sendTransaction"
        tx_hash = create_block_hash(b'txHash')
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        value = 10 * 10 ** 18
        step_limit = 1000
        nonce = 123
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
        data_type = "call"
        data_method = "transfer"
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "block": {
                "blockHeight": hex(block_height),
                "blockHash": bytes.hex(block_hash),
                "timestamp": hex(timestamp),
                "prevBlockHash": bytes.hex(prev_block_hash)
            },
            "transactions": [
                {
                    "method": method,
                    "params": {
                        "txHash": bytes.hex(tx_hash),
                        "version": hex(version),
                        "from": str(from_addr),
                        "to": str(to_addr),
                        "value": hex(value),
                        "stepLimit": hex(step_limit),
                        "timestamp": hex(timestamp),
                        "nonce": hex(nonce),
                        "signature": signature,
                        "dataType": data_type,
                        "data": {
                            "method": data_method,
                            "params": {
                                "from": str(data_from),
                                "to": str(data_to),
                                "value": hex(data_value)
                            }
                        }
                    }
                }
            ]
        }

        ret_params = TypeConverter.convert(request_params, ParamType.INVOKE)

        self.assertEqual(block_height, ret_params['block']['blockHeight'])
        self.assertEqual(block_hash, ret_params['block']['blockHash'])
        self.assertEqual(timestamp, ret_params['block']['timestamp'])
        self.assertEqual(prev_block_hash, ret_params['block']['prevBlockHash'])

        self.assertEqual(method, ret_params['transactions'][0]['method'])
        self.assertEqual(tx_hash, ret_params['transactions'][0]['params']['txHash'])
        self.assertEqual(version, ret_params['transactions'][0]['params']['version'])
        self.assertEqual(from_addr, ret_params['transactions'][0]['params']['from'])
        self.assertEqual(to_addr, ret_params['transactions'][0]['params']['to'])
        self.assertEqual(value, ret_params['transactions'][0]['params']['value'])
        self.assertEqual(step_limit, ret_params['transactions'][0]['params']['stepLimit'])
        self.assertEqual(timestamp, ret_params['transactions'][0]['params']['timestamp'])
        self.assertEqual(nonce, ret_params['transactions'][0]['params']['nonce'])
        self.assertEqual(signature, ret_params['transactions'][0]['params']['signature'])
        self.assertEqual(data_type, ret_params['transactions'][0]['params']['dataType'])
        self.assertEqual(data_method, ret_params['transactions'][0]['params']['data']['method'])
        self.assertNotEqual(data_from, ret_params['transactions'][0]['params']['data']['params']['from'])
        self.assertNotEqual(data_to, ret_params['transactions'][0]['params']['data']['params']['to'])
        self.assertNotEqual(data_value, ret_params['transactions'][0]['params']['data']['params']['value'])

    def test_icx_call_convert(self):
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        data_type = "call"
        data_method = "get_balance"
        data_addr = create_address(AddressPrefix.EOA, b'data_addr')

        request_params = {
            "version": hex(version),
            "from": str(from_addr),
            "to": str(to_addr),
            "dataType": data_type,
            "data": {
                "method": data_method,
                "params": {
                    "address": str(data_addr),
                }
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.ICX_CALL)

        self.assertEqual(version, ret_params['version'])
        self.assertEqual(from_addr, ret_params['from'])
        self.assertEqual(to_addr, ret_params['to'])
        self.assertEqual(data_type, ret_params['dataType'])
        self.assertEqual(data_method, ret_params['data']['method'])
        self.assertNotEqual(data_addr, ret_params['data']['params']['address'])

    def test_icx_get_balance_convert(self):
        version = 3
        addr1 = create_address(AddressPrefix.EOA, b'addr1')

        request_params = {
            "version": hex(version),
            "address": str(addr1)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.ICX_GET_BALANCE)

        self.assertEqual(version, ret_params['version'])
        self.assertEqual(addr1, ret_params['address'])

    def test_icx_total_supply_convert(self):
        version = 3
        request_params = {
            "version": hex(version)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.ICX_GET_TOTAL_SUPPLY)

        self.assertEqual(version, ret_params['version'])

    def test_icx_get_score_api_convert(self):
        version = 3
        score_addr = create_address(AddressPrefix.CONTRACT, b'score')

        request_params = {
            "version": hex(version),
            "address": str(score_addr)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.ICX_GET_SCORE_API)

        self.assertEqual(version, ret_params['version'])
        self.assertEqual(score_addr, ret_params['address'])

    def test_query_convert1(self):
        method = "icx_call"
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        data_type = "call"
        data_method = "get_balance"
        data_addr = create_address(AddressPrefix.EOA, b'data_addr')

        request_params = {
            "method": method,
            "params": {
                "version": hex(version),
                "from": str(from_addr),
                "to": str(to_addr),
                "dataType": data_type,
                "data": {
                    "method": data_method,
                    "params": {
                        "address": str(data_addr),
                    }
                }
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.QUERY)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(from_addr, ret_params['params']['from'])
        self.assertEqual(to_addr, ret_params['params']['to'])
        self.assertEqual(data_type, ret_params['params']['dataType'])
        self.assertEqual(data_method, ret_params['params']['data']['method'])
        self.assertNotEqual(data_addr, ret_params['params']['data']['params']['address'])

    def test_query_convert2(self):
        method = "icx_getBalance"
        version = 3
        addr1 = create_address(AddressPrefix.EOA, b'addr1')

        request_params = {
            "method": method,
            "params": {
                "version": hex(version),
                "address": str(addr1)
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.QUERY)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(addr1, ret_params['params']['address'])

    def test_query_convert3(self):
        method = "icx_getTotalSupply"
        version = 3

        request_params = {
            "method": method,
            "params": {
                "version": hex(version)
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.QUERY)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(version, ret_params['params']['version'])

    def test_query_convert4(self):
        method = "icx_getScoreApi"
        version = 3
        addr1 = create_address(AddressPrefix.EOA, b'addr1')

        request_params = {
            "method": method,
            "params": {
                "version": hex(version),
                "address": str(addr1)
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.QUERY)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(addr1, ret_params['params']['address'])

    def test_write_precommit_convert(self):
        block_height = 1001
        block_hash = create_block_hash(b'block1')

        request_params = {
            "blockHeight": hex(block_height),
            "blockHash": bytes.hex(block_hash)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.WRITE_PRECOMMIT)

        self.assertEqual(block_height, ret_params['blockHeight'])
        self.assertEqual(block_hash, ret_params['blockHash'])

    def test_remove_precommit_convert(self):
        block_height = 1001
        block_hash = create_block_hash(b'block1')

        request_params = {
            "blockHeight": hex(block_height),
            "blockHash": bytes.hex(block_hash)
        }

        ret_params = TypeConverter.convert(request_params, ParamType.REMOVE_PRECOMMIT)

        self.assertEqual(block_height, ret_params['blockHeight'])
        self.assertEqual(block_hash, ret_params['blockHash'])

    def test_validate_tx_convert(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash(b'txHash')
        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        value = 10 * 10 ** 18
        step_limit = 1000
        timestamp = 12345
        nonce = 123
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
        data_type = "call"
        data_method = "transfer"
        data_from = create_address(AddressPrefix.EOA, b'data_from')
        data_to = create_address(AddressPrefix.EOA, b'data_to')
        data_value = 1 * 10 ** 18

        request_params = {
            "method": method,
            "params": {
                "txHash": bytes.hex(tx_hash),
                "version": hex(version),
                "from": str(from_addr),
                "to": str(to_addr),
                "value": hex(value),
                "stepLimit": hex(step_limit),
                "timestamp": hex(timestamp),
                "nonce": hex(nonce),
                "signature": signature,
                "dataType": data_type,
                "data": {
                    "method": data_method,
                    "params": {
                        "from": str(data_from),
                        "to": str(data_to),
                        "value": hex(data_value)
                    }
                }
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.VALIDATE_TRANSACTION)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(tx_hash, ret_params['params']['txHash'])
        self.assertEqual(version, ret_params['params']['version'])
        self.assertEqual(from_addr, ret_params['params']['from'])
        self.assertEqual(to_addr, ret_params['params']['to'])
        self.assertEqual(value, ret_params['params']['value'])
        self.assertEqual(step_limit, ret_params['params']['stepLimit'])
        self.assertEqual(timestamp, ret_params['params']['timestamp'])
        self.assertEqual(nonce, ret_params['params']['nonce'])
        self.assertEqual(signature, ret_params['params']['signature'])
        self.assertEqual(data_type, ret_params['params']['dataType'])
        self.assertEqual(data_method, ret_params['params']['data']['method'])
        self.assertNotEqual(data_from, ret_params['params']['data']['params']['from'])
        self.assertNotEqual(data_to, ret_params['params']['data']['params']['to'])
        self.assertNotEqual(data_value, ret_params['params']['data']['params']['value'])

    def test_v2_invoke_convert(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash(b'txHash')
        from_addr = create_address(AddressPrefix.EOA, b'from')
        to_addr = create_address(AddressPrefix.CONTRACT, b'score')
        value = 10 * 10 ** 18
        fee = 10 * 10 ** 16
        timestamp = 12345
        nonce = 123
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "method": method,
            "params": {
                "tx_hash": bytes.hex(tx_hash),
                "from": str(from_addr),
                "to": str(to_addr),
                "value": hex(value),
                "fee": hex(fee),
                "timestamp": hex(timestamp),
                "nonce": hex(nonce),
                "signature": signature
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.VALIDATE_TRANSACTION)

        self.assertEqual(method, ret_params['method'])
        self.assertEqual(tx_hash, ret_params['params']['txHash'])
        self.assertEqual(from_addr, ret_params['params']['from'])
        self.assertEqual(to_addr, ret_params['params']['to'])
        self.assertEqual(value, ret_params['params']['value'])
        self.assertEqual(fee, ret_params['params']['fee'])
        self.assertEqual(timestamp, ret_params['params']['timestamp'])
        self.assertEqual(nonce, ret_params['params']['nonce'])
        self.assertEqual(signature, ret_params['params']['signature'])
