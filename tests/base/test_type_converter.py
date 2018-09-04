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

import unittest

from iconservice.base.exception import ExceptionCode
from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType, ConstantKeys
from tests import create_block_hash, create_address

from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestTypeConverter(unittest.TestCase):

    def setUp(self):
        self.signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="
        self.content = "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e"
        self.icx_factor = 10 ** 18
        self.icx_fee = 10 ** 16

    def test_block_convert(self):
        block_height = 1001
        timestamp = 12345
        self._test_block_convert(block_height, timestamp)

    def test_block_convert_negative_int(self):
        block_height = -1001
        timestamp = -12345
        self._test_block_convert(block_height, timestamp)

    def _test_block_convert(self, block_height: int, timestamp: int):
        block_hash = create_block_hash()
        prev_block_hash = create_block_hash()

        request = {
            ConstantKeys.BLOCK_HEIGHT: hex(block_height),
            ConstantKeys.BLOCK_HASH: bytes.hex(block_hash),
            ConstantKeys.TIMESTAMP: hex(timestamp),
            ConstantKeys.PREV_BLOCK_HASH: bytes.hex(prev_block_hash)
        }

        ret_params = TypeConverter.convert(request, ParamType.BLOCK)

        self.assertEqual(block_height, ret_params[ConstantKeys.BLOCK_HEIGHT])
        self.assertEqual(block_hash, ret_params[ConstantKeys.BLOCK_HASH])
        self.assertEqual(timestamp, ret_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(prev_block_hash, ret_params[ConstantKeys.PREV_BLOCK_HASH])

    def test_account_convert(self):
        balance = 10000 * self.icx_factor
        self._test_account_convert(balance)

    def test_account_convert_negative_int(self):
        balance = -10000 * self.icx_factor
        self._test_account_convert(balance)

    def _test_account_convert(self, balance: int):
        name = 'genesis'
        address = create_address()

        request = {
            ConstantKeys.NAME: name,
            ConstantKeys.ADDRESS: str(address),
            ConstantKeys.BALANCE: hex(balance)
        }

        ret_params = TypeConverter.convert(request, ParamType.ACCOUNT_DATA)

        self.assertEqual(name, ret_params[ConstantKeys.NAME])
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])
        self.assertEqual(balance, ret_params[ConstantKeys.BALANCE])

    def test_call_data_convert(self):
        method = 'icx_sendTransaction'
        data_from = create_address()
        data_to = create_address()
        data_value = 1 * self.icx_factor

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS:
                {
                    ConstantKeys.FROM: str(data_from),
                    ConstantKeys.TO: str(data_to),
                    ConstantKeys.VALUE: hex(data_value)
                }
        }

        ret_params = TypeConverter.convert(request, ParamType.CALL_DATA)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])
        params = ret_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_from, params[ConstantKeys.FROM])
        self.assertNotEqual(data_to, params[ConstantKeys.TO])
        self.assertNotEqual(data_value, params[ConstantKeys.VALUE])

    def test_deploy_data_convert(self):
        content_type = 'application/zip'
        content = self.content
        data_from = create_address()
        data_to = create_address()
        data_value = 1 * self.icx_factor

        request = {
            ConstantKeys.CONTENT_TYPE: content_type,
            ConstantKeys.CONTENT: content,
            ConstantKeys.PARAMS:
                {
                    ConstantKeys.FROM: str(data_from),
                    ConstantKeys.TO: str(data_to),
                    ConstantKeys.VALUE: hex(data_value)
                }
        }

        ret_params = TypeConverter.convert(request, ParamType.DEPLOY_DATA)

        self.assertEqual(content_type, ret_params[ConstantKeys.CONTENT_TYPE])
        self.assertEqual(content, ret_params[ConstantKeys.CONTENT])
        params = ret_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_from, params[ConstantKeys.FROM])
        self.assertNotEqual(data_to, params[ConstantKeys.TO])
        self.assertNotEqual(data_value, params[ConstantKeys.VALUE])

    def test_transaction_convert_success1(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        from_addr = create_address()
        to_addr = create_address(1)
        value = 10 * self.icx_factor
        data_type = "call"
        data_method = "transfer"

        self._test_transaction_convert(method, tx_hash, from_addr, to_addr, value, data_type,
                                       data_method=data_method)

    def test_transaction_convert_success2(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        from_addr = create_address()
        to_addr = create_address(1)
        value = 10 * self.icx_factor

        data_type = "deploy"
        content_type = "application/zip"
        content = self.content

        self._test_transaction_convert(method, tx_hash, from_addr, to_addr, value, data_type,
                                       content_type=content_type, content=content)

    def test_transaction_convert_fail1(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        from_addr = create_address()
        to_addr = ""
        value = 10 * self.icx_factor
        data_type = "deploy"
        content_type = "application/zip"
        content = self.content

        with self.assertRaises(BaseException) as e:
            self._test_transaction_convert(method, tx_hash, from_addr, to_addr, value, data_type,
                                           content_type=content_type, content=content)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, "Invalid address")

    def test_transaction_convert_fail2(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        from_addr = create_address()
        to_addr = None
        value = 10 * self.icx_factor
        data_type = "deploy"
        content_type = "application/zip"
        content = self.content

        with self.assertRaises(BaseException) as e:
            self._test_transaction_convert(method, tx_hash, from_addr, to_addr, value, data_type,
                                           content_type=content_type, content=content)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, "TypeConvert Exception None value, template: ValueType.ADDRESS")

    def _test_transaction_convert(self,
                                  method: str,
                                  tx_hash: Optional[bytes],
                                  from_addr: 'Address',
                                  to_addr: Union[str, 'Address', None],
                                  value: int,
                                  data_type: str,
                                  data_method: Optional[str] = None,
                                  content_type: Optional[str] = None,
                                  content: Optional[str] = None):
        if to_addr is not None:
            req_to_addr = str(to_addr)
        else:
            req_to_addr = to_addr

        version = 3
        step_limit = 1000
        timestamp = 12345
        nonce = 123
        signature = self.signature
        data_from = create_address()
        data_to = create_address()
        data_value = 1 * self.icx_factor

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.VERSION: hex(version),
                ConstantKeys.FROM: str(from_addr),
                ConstantKeys.TO: req_to_addr,
                ConstantKeys.VALUE: hex(value),
                ConstantKeys.STEP_LIMIT: hex(step_limit),
                ConstantKeys.TIMESTAMP: hex(timestamp),
                ConstantKeys.NONCE: hex(nonce),
                ConstantKeys.SIGNATURE: signature,
                ConstantKeys.DATA_TYPE: data_type,
                ConstantKeys.DATA: {
                    ConstantKeys.PARAMS: {
                        ConstantKeys.FROM: str(data_from),
                        ConstantKeys.TO: str(data_to),
                        ConstantKeys.VALUE: hex(data_value)
                    }
                }
            }
        }

        params_params = request[ConstantKeys.PARAMS]
        if tx_hash:
            params_params[ConstantKeys.TX_HASH] = bytes.hex(tx_hash)
        data_params: dict = request[ConstantKeys.PARAMS][ConstantKeys.DATA]
        if data_method:
            data_params[ConstantKeys.METHOD] = data_method
        if content_type:
            data_params[ConstantKeys.CONTENT_TYPE] = content_type
        if content:
            data_params[ConstantKeys.CONTENT] = content

        ret_params = TypeConverter.convert(request, ParamType.INVOKE_TRANSACTION)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])
        params_params = ret_params[ConstantKeys.PARAMS]
        if tx_hash:
            self.assertEqual(tx_hash, params_params[ConstantKeys.TX_HASH])
        self.assertEqual(version, params_params[ConstantKeys.VERSION])
        self.assertEqual(from_addr, params_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, params_params[ConstantKeys.TO])
        self.assertEqual(value, params_params[ConstantKeys.VALUE])
        self.assertEqual(step_limit, params_params[ConstantKeys.STEP_LIMIT])
        self.assertEqual(timestamp, params_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(nonce, params_params[ConstantKeys.NONCE])
        self.assertEqual(signature, params_params[ConstantKeys.SIGNATURE])
        self.assertEqual(data_type, params_params[ConstantKeys.DATA_TYPE])

        data_params = params_params[ConstantKeys.DATA]
        if data_method:
            self.assertEqual(data_method, data_params[ConstantKeys.METHOD])
        if content_type:
            self.assertEqual(content_type, data_params[ConstantKeys.CONTENT_TYPE])
        if content:
            self.assertEqual(content, data_params[ConstantKeys.CONTENT])

        data_params_params = data_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_from, data_params_params[ConstantKeys.FROM])
        self.assertNotEqual(data_to, data_params_params[ConstantKeys.TO])
        self.assertNotEqual(data_value, data_params_params[ConstantKeys.VALUE])

    def test_invoke_convert(self):
        block_height = 1001
        block_hash = create_block_hash()
        timestamp = 12345
        prev_block_hash = create_block_hash()

        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        version = 3
        from_addr = create_address()
        to_addr = create_address(1)
        value = 10 * 10 ** 18
        step_limit = 1000
        nonce = 123
        signature = self.signature
        data_type = "call"
        data_method = "transfer"
        data_from = create_address()
        data_to = create_address()
        data_value = 1 * 10 ** 18
        fixed_fee = 10 ** 16

        request = {
            ConstantKeys.BLOCK: {
                ConstantKeys.BLOCK_HEIGHT: hex(block_height),
                ConstantKeys.BLOCK_HASH: bytes.hex(block_hash),
                ConstantKeys.TIMESTAMP: hex(timestamp),
                ConstantKeys.PREV_BLOCK_HASH: bytes.hex(prev_block_hash)
            },
            ConstantKeys.TRANSACTIONS: [
                {
                    ConstantKeys.METHOD: method,
                    ConstantKeys.PARAMS: {
                        ConstantKeys.TX_HASH: bytes.hex(tx_hash),
                        ConstantKeys.VERSION: hex(version),
                        ConstantKeys.FROM: str(from_addr),
                        ConstantKeys.TO: str(to_addr),
                        ConstantKeys.VALUE: hex(value),
                        ConstantKeys.STEP_LIMIT: hex(step_limit),
                        ConstantKeys.TIMESTAMP: hex(timestamp),
                        ConstantKeys.NONCE: hex(nonce),
                        ConstantKeys.SIGNATURE: signature,
                        ConstantKeys.DATA_TYPE: data_type,
                        ConstantKeys.DATA: {
                            ConstantKeys.METHOD: data_method,
                            ConstantKeys.PARAMS: {
                                ConstantKeys.FROM: str(data_from),
                                ConstantKeys.TO: str(data_to),
                                ConstantKeys.VALUE: hex(data_value)
                            }
                        }
                    }
                },
                {
                    ConstantKeys.METHOD: method,
                    ConstantKeys.PARAMS: {
                        ConstantKeys.TX_HASH: bytes.hex(tx_hash),
                        ConstantKeys.FROM: str(from_addr),
                        ConstantKeys.TO: str(to_addr),
                        ConstantKeys.VALUE: hex(value)[2:],
                        ConstantKeys.FEE: hex(fixed_fee),
                        ConstantKeys.TIMESTAMP: hex(timestamp),
                        ConstantKeys.NONCE: hex(nonce),
                        ConstantKeys.SIGNATURE: signature,
                    }
                }
            ]
        }

        ret_params = TypeConverter.convert(request, ParamType.INVOKE)

        block_params = ret_params[ConstantKeys.BLOCK]
        self.assertEqual(block_height, block_params[ConstantKeys.BLOCK_HEIGHT])
        self.assertEqual(block_hash, block_params[ConstantKeys.BLOCK_HASH])
        self.assertEqual(timestamp, block_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(prev_block_hash, block_params[ConstantKeys.PREV_BLOCK_HASH])

        transaction_params = ret_params[ConstantKeys.TRANSACTIONS][0]
        self.assertEqual(method, transaction_params[ConstantKeys.METHOD])

        transaction_params_params = transaction_params[ConstantKeys.PARAMS]
        self.assertEqual(tx_hash, transaction_params_params[ConstantKeys.TX_HASH])
        self.assertEqual(version, transaction_params_params[ConstantKeys.VERSION])
        self.assertEqual(from_addr, transaction_params_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, transaction_params_params[ConstantKeys.TO])
        self.assertEqual(value, transaction_params_params[ConstantKeys.VALUE])
        self.assertEqual(step_limit, transaction_params_params[ConstantKeys.STEP_LIMIT])
        self.assertEqual(timestamp, transaction_params_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(nonce, transaction_params_params[ConstantKeys.NONCE])
        self.assertEqual(signature, transaction_params_params[ConstantKeys.SIGNATURE])
        self.assertEqual(data_type, transaction_params_params[ConstantKeys.DATA_TYPE])

        transaction_data_params = transaction_params_params[ConstantKeys.DATA]
        self.assertEqual(data_method, transaction_data_params[ConstantKeys.METHOD])

        transaction_data_params_params = transaction_data_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_from, transaction_data_params_params[ConstantKeys.FROM])
        self.assertNotEqual(data_to, transaction_data_params_params[ConstantKeys.TO])
        self.assertNotEqual(data_value, transaction_data_params_params[ConstantKeys.VALUE])

        # Check the 2nd tx (v2)
        transaction_params = ret_params[ConstantKeys.TRANSACTIONS][1]
        transaction_params_params = transaction_params[ConstantKeys.PARAMS]
        self.assertEqual(tx_hash, transaction_params_params[ConstantKeys.TX_HASH])
        self.assertEqual(from_addr, transaction_params_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, transaction_params_params[ConstantKeys.TO])
        self.assertEqual(value, transaction_params_params[ConstantKeys.VALUE])
        self.assertEqual(fixed_fee, transaction_params_params[ConstantKeys.FEE])
        self.assertEqual(timestamp, transaction_params_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(nonce, transaction_params_params[ConstantKeys.NONCE])
        self.assertEqual(signature, transaction_params_params[ConstantKeys.SIGNATURE])

    def test_genesis_invoke_convert(self):
        block_height = 1001
        block_hash = create_block_hash()
        timestamp = 12345
        prev_block_hash = create_block_hash()

        accounts = [
            {
                "name": "god",
                "address": create_address(),
                "balance": 10 * self.icx_factor
            },
            {
                "name": "treasury",
                "address": create_address(),
                "balance": 0
            },
        ]

        message = "hello icon!"

        request = {
                ConstantKeys.BLOCK: {
                    ConstantKeys.BLOCK_HEIGHT: hex(block_height),
                    ConstantKeys.BLOCK_HASH: bytes.hex(block_hash),
                    ConstantKeys.TIMESTAMP: hex(timestamp),
                    ConstantKeys.PREV_BLOCK_HASH: bytes.hex(prev_block_hash)
                },
                ConstantKeys.TRANSACTIONS: [
                    {
                        ConstantKeys.METHOD: "icx_sendTransaction",
                        ConstantKeys.PARAMS: {
                            ConstantKeys.TX_HASH: bytes.hex(create_block_hash())
                        },
                        ConstantKeys.GENESIS_DATA: {
                            ConstantKeys.ACCOUNTS: [
                                {
                                    ConstantKeys.NAME: accounts[0][ConstantKeys.NAME],
                                    ConstantKeys.ADDRESS: str(accounts[0][ConstantKeys.ADDRESS]),
                                    ConstantKeys.BALANCE: hex(accounts[0][ConstantKeys.BALANCE])
                                },
                                {
                                    ConstantKeys.NAME: accounts[1][ConstantKeys.NAME],
                                    ConstantKeys.ADDRESS: str(accounts[1][ConstantKeys.ADDRESS]),
                                    ConstantKeys.BALANCE: hex(accounts[1][ConstantKeys.BALANCE])
                                }
                            ],
                            ConstantKeys.MESSAGE: message
                        }
                    }
                ],
            }

        ret_params = TypeConverter.convert(request, ParamType.INVOKE)

        block_params = ret_params[ConstantKeys.BLOCK]
        self.assertEqual(block_height, block_params[ConstantKeys.BLOCK_HEIGHT])
        self.assertEqual(block_hash, block_params[ConstantKeys.BLOCK_HASH])
        self.assertEqual(timestamp, block_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(prev_block_hash, block_params[ConstantKeys.PREV_BLOCK_HASH])

        transaction_params = ret_params[ConstantKeys.TRANSACTIONS][0]
        genesis_params = transaction_params[ConstantKeys.GENESIS_DATA]
        accounts_params = genesis_params[ConstantKeys.ACCOUNTS]
        for index, account_params in enumerate(accounts_params):
            self.assertEqual(account_params[ConstantKeys.NAME], accounts[index][ConstantKeys.NAME])
            self.assertEqual(account_params[ConstantKeys.ADDRESS], accounts[index][ConstantKeys.ADDRESS])
            self.assertEqual(account_params[ConstantKeys.BALANCE], accounts[index][ConstantKeys.BALANCE])
        self.assertEqual(genesis_params[ConstantKeys.MESSAGE], message)

    def test_icx_call_convert(self):
        version = 3
        from_addr = create_address()
        to_addr = create_address(1)
        data_type = "call"
        data_method = "get_balance"
        data_addr = create_address()

        request = {
            ConstantKeys.VERSION: hex(version),
            ConstantKeys.FROM: str(from_addr),
            ConstantKeys.TO: str(to_addr),
            ConstantKeys.DATA_TYPE: data_type,
            ConstantKeys.DATA: {
                ConstantKeys.METHOD: data_method,
                ConstantKeys.PARAMS: {
                    ConstantKeys.ADDRESS: str(data_addr)
                }
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.ICX_CALL)

        self.assertEqual(version, ret_params[ConstantKeys.VERSION])
        self.assertEqual(from_addr, ret_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, ret_params[ConstantKeys.TO])
        self.assertEqual(data_type, ret_params[ConstantKeys.DATA_TYPE])

        data_params = ret_params[ConstantKeys.DATA]
        self.assertEqual(data_method, data_params[ConstantKeys.METHOD])
        data_params_params = data_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_addr, data_params_params[ConstantKeys.ADDRESS])

    def test_icx_get_balance_convert(self):
        version = 3
        addr1 = create_address()

        request = {
            ConstantKeys.VERSION: hex(version),
            ConstantKeys.ADDRESS: str(addr1)
        }

        ret_params = TypeConverter.convert(request, ParamType.ICX_GET_BALANCE)

        self.assertEqual(version, ret_params[ConstantKeys.VERSION])
        self.assertEqual(addr1, ret_params[ConstantKeys.ADDRESS])

    def test_icx_total_supply_convert(self):
        version = 3

        request = {
            ConstantKeys.VERSION: hex(version)
        }

        ret_params = TypeConverter.convert(request, ParamType.ICX_GET_TOTAL_SUPPLY)

        self.assertEqual(version, ret_params[ConstantKeys.VERSION])

    def test_icx_get_score_api_convert(self):
        version = 3

        score_addr = create_address(1)

        request = {
            ConstantKeys.VERSION: hex(version),
            ConstantKeys.ADDRESS: str(score_addr)
        }

        ret_params = TypeConverter.convert(request, ParamType.ICX_GET_SCORE_API)

        self.assertEqual(version, ret_params[ConstantKeys.VERSION])
        self.assertEqual(score_addr, ret_params[ConstantKeys.ADDRESS])

    def test_query_convert_icx_call(self):
        method = "icx_call"
        version = 3
        from_addr = create_address()
        to_addr = create_address(1)
        data_type = "call"
        data_method = "get_balance"
        data_addr = create_address()

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.VERSION: hex(version),
                ConstantKeys.FROM: str(from_addr),
                ConstantKeys.TO: str(to_addr),
                ConstantKeys.DATA_TYPE: data_type,
                ConstantKeys.DATA: {
                    ConstantKeys.METHOD: data_method,
                    ConstantKeys.PARAMS: {
                        ConstantKeys.ADDRESS: str(data_addr),
                    }
                }
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.QUERY)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])

        params_params = ret_params[ConstantKeys.PARAMS]
        self.assertEqual(version, params_params[ConstantKeys.VERSION])
        self.assertEqual(from_addr, params_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, params_params[ConstantKeys.TO])
        self.assertEqual(data_type, params_params[ConstantKeys.DATA_TYPE])

        data_params = params_params[ConstantKeys.DATA]
        self.assertEqual(data_method, data_params[ConstantKeys.METHOD])

        data_params_params = data_params[ConstantKeys.PARAMS]
        self.assertNotEqual(data_addr, data_params_params[ConstantKeys.ADDRESS])

    def test_query_convert_icx_get_balance(self):
        method = "icx_getBalance"
        version = 3
        addr1 = create_address()

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.VERSION: hex(version),
                ConstantKeys.ADDRESS: str(addr1)
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.QUERY)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])

        params_params = ret_params[ConstantKeys.PARAMS]
        self.assertEqual(version, params_params[ConstantKeys.VERSION])
        self.assertEqual(addr1, params_params[ConstantKeys.ADDRESS])

    def test_query_convert_icx_get_total_supply(self):
        method = "icx_getTotalSupply"
        version = 3

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.VERSION: hex(version)
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.QUERY)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])

        params_params = ret_params[ConstantKeys.PARAMS]
        self.assertEqual(version, params_params[ConstantKeys.VERSION])

    def test_query_convert_icx_get_score_api(self):
        method = "icx_getScoreApi"
        version = 3
        addr1 = create_address()

        request = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.VERSION: hex(version),
                ConstantKeys.ADDRESS: str(addr1)
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.QUERY)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])

        params_params = ret_params[ConstantKeys.PARAMS]
        self.assertEqual(version, params_params[ConstantKeys.VERSION])
        self.assertEqual(addr1, params_params[ConstantKeys.ADDRESS])

    def test_write_precommit_convert(self):
        block_height = 1001
        block_hash = create_block_hash()

        request = {
            ConstantKeys.BLOCK_HEIGHT: hex(block_height),
            ConstantKeys.BLOCK_HASH: bytes.hex(block_hash)
        }

        ret_params = TypeConverter.convert(request, ParamType.WRITE_PRECOMMIT)

        self.assertEqual(block_height, ret_params[ConstantKeys.BLOCK_HEIGHT])
        self.assertEqual(block_hash, ret_params[ConstantKeys.BLOCK_HASH])

    def test_remove_precommit_convert(self):
        block_height = 1001
        block_hash = create_block_hash()

        request = {
            ConstantKeys.BLOCK_HEIGHT: hex(block_height),
            ConstantKeys.BLOCK_HASH: bytes.hex(block_hash)
        }

        ret_params = TypeConverter.convert(request, ParamType.REMOVE_PRECOMMIT)

        self.assertEqual(block_height, ret_params[ConstantKeys.BLOCK_HEIGHT])
        self.assertEqual(block_hash, ret_params[ConstantKeys.BLOCK_HASH])

    def test_validate_tx_convert(self):
        method = "icx_sendTransaction"
        from_addr = create_address()
        to_addr = create_address(1)
        value = 10 * 10 ** 18

        data_type = "call"
        data_method = "transfer"

        self._test_transaction_convert(method, None, from_addr, to_addr, value, data_type,
                                       data_method=data_method)

    def test_v2_invoke_convert(self):
        method = "icx_sendTransaction"
        tx_hash = create_block_hash()
        from_addr = create_address()
        to_addr = create_address(1)
        value = 10 * self.icx_factor
        fee = 10 * self.icx_fee
        timestamp = 12345
        nonce = 123
        signature = self.signature

        request_params = {
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {
                ConstantKeys.OLD_TX_HASH: bytes.hex(tx_hash),
                ConstantKeys.FROM: str(from_addr),
                ConstantKeys.TO: str(to_addr),
                ConstantKeys.VALUE: hex(value),
                ConstantKeys.FEE: hex(fee),
                ConstantKeys.TIMESTAMP: hex(timestamp),
                ConstantKeys.NONCE: hex(nonce),
                ConstantKeys.SIGNATURE: signature
            }
        }

        ret_params = TypeConverter.convert(request_params, ParamType.VALIDATE_TRANSACTION)

        self.assertEqual(method, ret_params[ConstantKeys.METHOD])

        params_params = ret_params[ConstantKeys.PARAMS]
        self.assertEqual(tx_hash, params_params[ConstantKeys.TX_HASH])
        self.assertEqual(from_addr, params_params[ConstantKeys.FROM])
        self.assertEqual(to_addr, params_params[ConstantKeys.TO])
        self.assertEqual(value, params_params[ConstantKeys.VALUE])
        self.assertEqual(fee, params_params[ConstantKeys.FEE])
        self.assertEqual(timestamp, params_params[ConstantKeys.TIMESTAMP])
        self.assertEqual(nonce, params_params[ConstantKeys.NONCE])
        self.assertEqual(signature, params_params[ConstantKeys.SIGNATURE])
