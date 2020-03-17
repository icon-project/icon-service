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

"""IconScoreEngine testcase
"""
import hashlib
import time
import unittest
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, MalformedAddress, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, InvalidParamsException, IconScoreException
from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType
from iconservice.icon_constant import ConfigKey
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.utils import icx_to_loop
from tests import create_block_hash, create_address, create_tx_hash, \
    raise_exception_start_tag, raise_exception_end_tag, create_timestamp
from tests.integrate_test.test_integrate_base import TestIntegrateBase, TOTAL_SUPPLY


class TestIconServiceEngine(TestIntegrateBase):

    def _genesis_invoke(self) -> tuple:
        tx_hash = create_tx_hash()
        timestamp_us = create_timestamp()
        request_params = {
            'txHash': tx_hash,
            'version': self._version,
            'timestamp': timestamp_us
        }

        tx = {
            'method': 'icx_sendTransaction',
            'params': request_params,
            'genesisData': {
                "accounts": [
                    {
                        "name": "genesis",
                        "address": self._genesis,
                        "balance": 0
                    },
                    {
                        "name": "fee_treasury",
                        "address": self._fee_treasury,
                        "balance": 0
                    },
                    {
                        "name": "_admin",
                        "address": self._admin.address,
                        "balance": icx_to_loop(TOTAL_SUPPLY)
                    }
                ]
            },
        }

        block_hash = create_block_hash()
        self.genesis_block = Block(self._block_height + 1, block_hash, timestamp_us, None, 0)
        invoke_response: tuple = self.icon_service_engine.invoke(
            self.genesis_block,
            [tx]
        )
        self.icon_service_engine.commit(self.genesis_block.height, self.genesis_block.hash, None)
        self._block_height += 1
        self._prev_block_hash = block_hash

        return invoke_response

    def setUp(self):
        super().setUp()
        self._to = create_address(AddressPrefix.EOA)
        self._governance_address = GOVERNANCE_SCORE_ADDRESS
        self._score_address = create_address(AddressPrefix.CONTRACT)

    def test_query(self):
        method = 'icx_getBalance'
        params = {'address': self._admin.address}

        balance = self.icon_service_engine.query(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self.get_total_supply(), balance)

    def test_invoke(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        step_limit = 200000000000000
        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'from': self._admin.address,
                'to': self._to,
                'value': value,
                'stepLimit': step_limit,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash,
                      0)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v3])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)

        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)
        self.assertNotEqual(tx_result.step_used, 0)
        self.assertEqual(tx_result.step_price, 0)

        self.icon_service_engine.commit(block.height, block_hash, None)

        # Check whether fee charging works well
        from_balance: int = self.get_balance(self._admin.address)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, icx_to_loop(TOTAL_SUPPLY) - value - fee)

    def test_invoke_v2_without_fee(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        tx_v2 = {
            'method': 'icx_sendTransaction',
            'params': {
                'from': self._admin.address,
                'to': self._to,
                'value': value,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height, block_hash, block_timestamp, self.genesis_block.hash, 0)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v2])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)
        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10 ** 6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)
        self.assertEqual(tx_result.step_price, 0)

        # Write updated states to levelDB
        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        from_balance: int = self.get_balance(self._admin.address)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, icx_to_loop(TOTAL_SUPPLY) - value - fee)

    def test_invoke_v2_with_zero_fee_and_malformed_to_address(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18
        to = MalformedAddress.from_string('')
        fixed_fee: int = 10 ** 16

        tx_v2 = {
            'method': 'icx_sendTransaction',
            'params': {
                'from': self._admin.address,
                'to': to,
                'value': value,
                'fee': fixed_fee,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height, block_hash, block_timestamp, self.genesis_block.hash, 0)
        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v2])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)
        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10**6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)

        self.assertEqual(tx_result.step_price, 0)

        # Write updated states to levelDB
        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        from_balance: int = self.get_balance(self._admin.address)
        to_balance: int = self.get_balance(to)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(0, fee)
        self.assertEqual(value, to_balance)
        self.assertEqual(from_balance, icx_to_loop(TOTAL_SUPPLY) - value - fee)

    def test_invoke_v3_without_fee(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'nid': 3,
                'version': 3,
                'from': self._admin.address,
                'to': self._to,
                'value': value,
                'stepLimit': 1000000,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash,
                      0)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v3])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)

        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10**6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)
        self.assertEqual(tx_result.step_price, 0)

        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        from_balance: int = self.get_balance(self._admin.address)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, icx_to_loop(TOTAL_SUPPLY) - value - fee)

    def test_invoke_v3_with_fee(self):
        table = {ConfigKey.SERVICE_FEE: True,
                 ConfigKey.SERVICE_AUDIT: False,
                 ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}
        # TODO : apply service flag
        self.icon_service_engine._flag = self.icon_service_engine._make_service_flag(table)

        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18
        step_limit = 1000000

        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'nid': 3,
                'version': 3,
                'from': self._admin.address,
                'to': self._to,
                'value': value,
                'stepLimit': step_limit,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash,
                      0)

        before_from_balance: int = self.get_balance(self._admin.address)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v3])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)

        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10**6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)

        # step_price = self.get_step_price()
        # if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.FEE):
        #     step_price MUST BE 10**10 on protocol v2
        #     self.assertEqual(
        #         step_price, self.icon_service_engine._step_counter_factory.get_step_price())
        # else:
        #     self.assertEqual(step_price, 0)
        # self.assertEqual(tx_result.step_price, step_price)

        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        after_from_balance: int = self.get_balance(self._admin.address)
        fee = tx_result.step_price * tx_result.step_used
        value = value if tx_result.status == TransactionResult.SUCCESS else 0
        self.assertEqual(after_from_balance, before_from_balance - value - fee)

    def test_score_invoke_with_revert(self):
        # TODO apply service flag and check if step has applied even score call reverted
        # table = {ConfigKey.SERVICE_FEE: True,
        #          ConfigKey.SERVICE_AUDIT: False,
        #          ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}
        # self.icon_service_engine._flag = self.icon_service_engine._make_service_flag(table)

        self.deploy_score("sample_scores", "sample_wrong_revert", self._admin.address)

        block_height = 2
        block_hash = create_block_hash(b'block')
        block_timestamp = 0
        tx_hash = create_tx_hash()

        self._to = create_address(AddressPrefix.CONTRACT)

        tx_v3 = {
            'method': "icx_sendTransaction",
            "params": {
                'from': self._admin,
                'to': self._score_address,
                'value': 0,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'txHash': tx_hash,
                'dataType': 'call',
                'data': {
                    'method': 'set_value',
                    'params': {
                        'value': 777
                    }
                }
            }
        }
        prev_hash = self.icon_service_engine._get_last_block().hash

        block = Block(block_height, block_hash, block_timestamp, prev_hash, 0)

        before_from_balance: int = self.get_balance(self._admin.address)
        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v3])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)

        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNotNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 0)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10**6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)

        # step_price = self.icon_service_engine._step_counter_factory.get_step_price()
        # if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.FEE):
        #     step_price MUST BE 10**10 on protocol v2
        #     self.assertEqual(
        #         step_price, self.icon_service_engine._step_counter_factory.get_step_price())
        # else:
        #     self.assertEqual(step_price, 0)
        # self.assertEqual(tx_result.step_price, step_price)

        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        after_from_balance: int = self.get_balance(self._admin.address)

        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(after_from_balance, before_from_balance - fee)

    def test_score_invoke_failure(self):
        block_height = 1
        block_hash = create_block_hash(b'block')
        block_timestamp = 0
        tx_hash = create_tx_hash()

        tx = {
            'method': "icx_sendTransaction",
            "params": {
                'from': self._admin,
                'to': self._score_address,
                'value': 0,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'txHash': tx_hash,
                'dataType': 'call',
                'data': {
                    'method': 'set_value',
                    'params': {
                        'value': 777
                    }
                }
            }
        }

        block = Block(block_height, block_hash, block_timestamp,
                      self.icon_service_engine._get_last_block().hash, 0)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)
        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNotNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 0)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)
        self.assertTrue(isinstance(tx_result, TransactionResult))
        self.assertEqual(TransactionResult.FAILURE, tx_result.status)
        self.assertEqual(self._score_address, tx_result.to)
        self.assertEqual(tx_hash, tx_result.tx_hash)
        self.assertIsNone(tx_result.score_address)

    def test_score_invoke_failure_by_readonly_external_call(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 0
        to = self._governance_address

        step_limit = 200000000
        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'txHash': tx_hash,
                'nid': 3,
                'version': 3,
                'from': self._admin.address,
                'to': to,
                'value': value,
                'stepLimit': step_limit,
                'timestamp': 1234567890,
                'dataType': 'call',
                'data': {
                    'method': 'getScoreStatus',
                    'params': {
                        'txHash': tx_hash
                    }
                },
                'signature': 'VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA='
            }
        }

        block = Block(block_height, block_hash, block_timestamp, self.genesis_block.hash, 0)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [tx_v3])
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)

        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNotNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 0)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

    def test_commit(self):
        block = Block(
            block_height=1,
            block_hash=create_block_hash(),
            timestamp=0,
            prev_hash=create_block_hash(),
            cumulative_fee=0)

        with self.assertRaises(InvalidParamsException) as cm:
            self.icon_service_engine.commit(block.height, block.hash, None)
        e = cm.exception
        self.assertEqual(ExceptionCode.INVALID_PARAMETER, e.code)
        self.assertTrue(e.message.startswith('No precommit data'))

    def test_commit_change_block_hash(self):
        block_height = 1
        self._to = create_address(AddressPrefix.CONTRACT)
        instant_block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()

        dummy_tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'nid': 3,
                'version': 3,
                'from': self._admin.address,
                'to': self._to,
                'value': 1 * 10 ** 18,
                'stepLimit': 1000000,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }
        block = Block(block_height,
                      instant_block_hash,
                      block_timestamp,
                      self.genesis_block.hash,
                      0)

        self.icon_service_engine.invoke(block, [dummy_tx])
        instant_block_hash = block.hash
        block_hash = create_block_hash()
        self.icon_service_engine.commit(block.height, instant_block_hash, block_hash)

        self.assertEqual(self.icon_service_engine._get_last_block().hash, block_hash)
        self.assertEqual(IconScoreContext.storage.icx.last_block.hash, block_hash)

    def test_rollback(self):
        block = Block(
            block_height=1,
            block_hash=create_block_hash(),
            timestamp=0,
            prev_hash=self.genesis_block.hash,
            cumulative_fee=0)

        block_result, state_root_hash, _, _ = self.icon_service_engine.invoke(block, [])
        self.assertIsInstance(block_result, list)
        self.assertEqual(state_root_hash, hashlib.sha3_256(b'').digest())

        self.icon_service_engine.remove_precommit_state(block.height, block.hash)
        self.assertIsNone(self.icon_service_engine._precommit_data_manager.get(block.hash))

    def test_invoke_v2_with_malformed_to_address_and_type_converter(self):
        to = ''
        to_address = MalformedAddress.from_string(to)
        fixed_fee: int = 10 ** 16
        value = 1 * 10 ** 18
        block_height = 1
        block_hash: bytes = create_block_hash(b'block')
        prev_block_hash: bytes = self.genesis_block.hash
        tx_hash: bytes = create_tx_hash(b'tx')
        timestamp: int = int(time.time() * 1000)

        request = {
            'block': {
                'blockHeight': hex(block_height),
                'blockHash': block_hash.hex(),
                'prevBlockHash': prev_block_hash.hex(),
                'timestamp': str(timestamp)
            },
            'transactions': [
                {
                    'method': 'icx_sendTransaction',
                    'params': {
                        'from': str(self._admin.address),
                        'to': to,
                        'fee': hex(fixed_fee),
                        'value': hex(value),
                        'timestamp': '0x574024617ae39',
                        'nonce': '0x1',
                        'signature': 'yKMiB12Os0ZK9+XYiBSwydvMXA0y/LS9HzmZwtczQ1VAK98/mGUOmpwTjByFArjdkx72GOWIOzu6eqyZnKeHBAE=',
                        'txHash': tx_hash.hex()
                    }
                }
            ]
        }

        params = TypeConverter.convert(request, ParamType.INVOKE)
        converted_block_params = params['block']
        block = Block.from_dict(converted_block_params)

        self.assertEqual(block_height, block.height)
        self.assertEqual(block_hash, block.hash)
        self.assertEqual(prev_block_hash, block.prev_hash)
        self.assertEqual(timestamp, block.timestamp)

        transactions: list = params['transactions']
        self.assertIsInstance(transactions[0]['params']['to'], MalformedAddress)

        tx_results, state_root_hash, _, _ = self.icon_service_engine.invoke(block, transactions)
        self.assertIsInstance(state_root_hash, bytes)
        self.assertEqual(len(state_root_hash), 32)
        self.assertEqual(len(tx_results), 1)

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertIsNone(tx_result.failure)
        self.assertIsNone(tx_result.score_address)
        self.assertEqual(tx_result.status, 1)
        self.assertEqual(tx_result.block_height, block_height)
        self.assertEqual(tx_result.block_hash, block_hash)
        self.assertEqual(tx_result.tx_index, 0)
        self.assertEqual(tx_result.tx_hash, tx_hash)

        # step_used MUST BE 10**6 on protocol v2
        self.assertEqual(tx_result.step_used, 10**6)

        self.assertEqual(tx_result.step_price, 0)

        # Write updated states to levelDB
        self.icon_service_engine.commit(block.height, block.hash, None)

        # Check whether fee charging works well
        from_balance: int = self.get_balance(self._admin.address)
        to_balance: int = self.get_balance(to_address)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(0, fee)
        self.assertEqual(value, to_balance)
        self.assertEqual(from_balance, icx_to_loop(TOTAL_SUPPLY) - value - fee)

    def test_get_balance_with_malformed_address_and_type_converter(self):
        malformed_addresses = [
            '',
            '12341234',
            'hx1234123456',
            'cf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf',
            'hxdf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf']

        method: str = 'icx_getBalance'

        for address in malformed_addresses:
            request = {'method': method, 'params': {'address': address}}

            converted_request = TypeConverter.convert(request, ParamType.QUERY)
            self.assertEqual(method, converted_request['method'])

            params: dict = converted_request['params']
            self.assertEqual(MalformedAddress.from_string(address), params['address'])

            balance: int = self.icon_service_engine.query(
                converted_request['method'], converted_request['params'])
            self.assertEqual(0, balance)


if __name__ == '__main__':
    unittest.main()
