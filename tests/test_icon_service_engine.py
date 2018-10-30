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
import os
import unittest
import time
from unittest.mock import Mock

from iconcommons.icon_config import IconConfig
from iconservice.base.address import Address, AddressPrefix, MalformedAddress
from iconservice.base.block import Block
from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType
from iconservice.base.exception import ExceptionCode, ServerErrorException, \
    RevertException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import IconServiceFlag, ConfigKey
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import StepType
from tests import create_block_hash, create_address, rmtree, create_tx_hash, \
    raise_exception_start_tag, raise_exception_end_tag

context_factory = IconScoreContextFactory(max_size=1)
TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


def _create_context(context_type: IconScoreContextType) -> IconScoreContext:
    context = context_factory.create(context_type)

    if context.type == IconScoreContextType.INVOKE:
        context.block_batch = BlockBatch()
        context.tx_batch = TransactionBatch()

    return context


class TestIconServiceEngine(unittest.TestCase):
    def setUp(self):
        self._state_db_root_path = '.db'
        self._score_root_path = '.score'

        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        engine = IconServiceEngine()
        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf(
            {
                ConfigKey.BUILTIN_SCORE_OWNER: str(create_address(AddressPrefix.EOA)),
                ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path
            }
        )
        # engine._load_builtin_scores = Mock()
        # engine._init_global_value_by_governance_score = Mock()
        engine.open(conf)
        self._engine = engine

        self._genesis_address = create_address(AddressPrefix.EOA)
        self._treasury_address = create_address(AddressPrefix.EOA)
        self._governance_score_address =\
            Address.from_string('cx0000000000000000000000000000000000000001')

        self.from_ = self._genesis_address
        self._to = create_address(AddressPrefix.EOA)
        self._icon_score_address = create_address(AddressPrefix.CONTRACT)
        self._total_supply = 100 * 10 ** 18

        accounts = [
            {
                'name': 'god',
                'address': self._genesis_address,
                'balance': self._total_supply
            },
            {
                'name': 'treasury',
                'address': self._treasury_address,
                'balance': 0
            }
        ]

        block = Block(0, create_block_hash(), 0, None)
        tx = {'method': '',
              'params': {'txHash': create_tx_hash()},
              'genesisData': {'accounts': accounts}}
        tx_lists = [tx]

        self._engine.invoke(block, tx_lists)
        self._engine.commit(block)
        self.genesis_block = block

    def tearDown(self):
        self._engine.close()

        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

    def test_make_flag(self):
        table = {ConfigKey.SERVICE_FEE: True,
                 ConfigKey.SERVICE_AUDIT: False,
                 ConfigKey.SERVICE_DEPLOYER_WHITELIST: False,
                 ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}
        flag = self._engine._make_service_flag(table)
        self.assertEqual(flag, IconServiceFlag.fee)

    def test_query(self):
        method = 'icx_getBalance'
        params = {'address': self.from_}

        balance = self._engine.query(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self._total_supply, balance)

    def test_call_on_query(self):
        context = context_factory.create(IconScoreContextType.QUERY)

        method = 'icx_getBalance'
        params = {'address': self.from_}

        balance = self._engine._call(context, method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self._total_supply, balance)

        context_factory.destroy(context)

    def test_call_on_invoke(self):
        context = _create_context(IconScoreContextType.INVOKE)

        from_ = self._genesis_address
        to = self._to
        value = 1 * 10 ** 18  # 1 coin
        fee = 10 ** 16  # 0.01 coin

        method = 'icx_sendTransaction'
        params = {
            'from': from_,
            'to': to,
            'value': value,
            'fee': fee,
            'timestamp': 1234567890,
            'txHash': create_tx_hash()
        }

        step_limit: int = params.get('stepLimit', 0)
        if params.get('version', 2) < 3:
            step_limit = self._engine._step_counter_factory.get_max_step_limit(
                context.type)

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=0,
                                 origin=from_,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))

        context.block = Mock(spec=Block)
        context.event_logs = []
        context.cumulative_step_used = Mock(spec=int)
        context.cumulative_step_used.attach_mock(Mock(), '__add__')
        context.step_counter: IconScoreStepCounter = self._engine._step_counter_factory.create(step_limit)

        IconScoreContextUtil._get_service_flag = Mock(return_value=IconScoreContext.icon_service_flag)
        self._engine._call(context, method, params)

        # from(genesis), to
        # no transfer to fee_treasury because fee charging is disabled
        tx_batch = context.tx_batch
        self.assertEqual(2, len(tx_batch))

        context_factory.destroy(context)

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
                'from': self._genesis_address,
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
                      self.genesis_block.hash)

        original_invoke_request = self._engine._invoke_request

        # noinspection PyUnusedLocal
        def intercept_invoke_req(*args, **kwargs):
            context: 'IconScoreContext' = args[0]
            request: dict = args[1]
            index: int = args[2]
            ret = original_invoke_request(context, request, index)

            # Requesting the very big number of step limit,
            # but there's a max step limit,
            # asserts max step limit is applied to step counting.
            self.assertNotEqual(step_limit, context.step_counter.step_limit)
            self.assertEqual(
                self._engine._step_counter_factory.get_max_step_limit(
                    context.type),
                context.step_counter.step_limit)
            return ret

        self._engine._invoke_request = Mock(side_effect=intercept_invoke_req)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v3])
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
        step_unit = self._engine._step_counter_factory.get_step_cost(
            StepType.DEFAULT)

        self.assertEqual(tx_result.step_used, step_unit)

        step_price = self._engine._get_step_price()

        if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.fee):
            # step_price MUST BE 10**10 on protocol v2
            self.assertEqual(step_price, 10 ** 10)
        else:
            self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        self._engine.commit(block)

        # Check whether fee charging works well
        from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, self._total_supply - value - fee)

    def test_invoke_v2_without_fee(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        tx_v2 = {
            'method': 'icx_sendTransaction',
            'params': {
                'from': self.from_,
                'to': self._to,
                'value': value,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v2])
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

        step_price = self._engine._get_step_price()
        # if self._engine._is_flag_on(IconServiceFlag.fee):
        #     # step_used MUST BE 10**10 on protocol v2
        #     self.assertEqual(step_price, 10 ** 10)
        # else:
        #     self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        # Write updated states to levelDB
        self._engine.commit(block)

        # Check whether fee charging works well
        from_balance: int = self._engine._icx_engine.get_balance(
            None, self.from_)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, self._total_supply - value - fee)

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
                'from': self.from_,
                'to': to,
                'value': value,
                'fee': fixed_fee,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v2])
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

        step_price = self._engine._get_step_price()
        self.assertEqual(tx_result.step_price, step_price)

        # Write updated states to levelDB
        self._engine.commit(block)

        # Check whether fee charging works well
        from_balance: int = self._engine._icx_engine.get_balance(
            None, self.from_)
        to_balance: int = self._engine._icx_engine.get_balance(None, to)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(0, fee)
        self.assertEqual(value, to_balance)
        self.assertEqual(from_balance, self._total_supply - value - fee)

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
                'from': self._genesis_address,
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
                      self.genesis_block.hash)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v3])
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
        step_unit = self._engine._step_counter_factory.get_step_cost(
            StepType.DEFAULT)

        self.assertEqual(tx_result.step_used, step_unit)

        step_price = self._engine._get_step_price()
        if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.fee):
            # step_used MUST BE 10**10 on protocol v2
            self.assertEqual(step_price, 10 ** 10)
        else:
            self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        self._engine.commit(block)

        # Check whether fee charging works well
        from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, self._total_supply - value - fee)

    def test_invoke_v3_with_fee(self):

        table = {ConfigKey.SERVICE_FEE: True,
                 ConfigKey.SERVICE_AUDIT: False,
                 ConfigKey.SERVICE_DEPLOYER_WHITELIST: False,
                 ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}
        # TODO: must apply the service flags to the engine
        # self._engine._flag = self._engine._make_service_flag(table)

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
                'from': self._genesis_address,
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
                      self.genesis_block.hash)

        before_from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v3])
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
        step_cost = self._engine._step_counter_factory.get_step_cost(
            StepType.DEFAULT)

        self.assertEqual(tx_result.step_used, step_cost)

        step_price = self._engine._get_step_price()
        if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.fee):
            # step_price MUST BE 10**10 on protocol v2
            self.assertEqual(
                step_price, self._engine._step_counter_factory.get_step_price())
        else:
            self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        self._engine.commit(block)

        # Check whether fee charging works well
        after_from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)
        fee = tx_result.step_price * tx_result.step_used
        value = value if tx_result.status == TransactionResult.SUCCESS else 0
        self.assertEqual(after_from_balance, before_from_balance - value - fee)

    def test_score_invoke_with_revert(self):

        table = {ConfigKey.SERVICE_FEE: True,
                 ConfigKey.SERVICE_AUDIT: False,
                 ConfigKey.SERVICE_DEPLOYER_WHITELIST: False,
                 ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}
        # TODO: must apply the service flags to the engine
        # self._engine._flag = self._engine._make_service_flag(table)

        block_height = 1
        block_hash = create_block_hash(b'block')
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        self._to = create_address(AddressPrefix.CONTRACT)

        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'from': self._genesis_address,
                'to': self._to,
                'value': value,
                'stepLimit': 20000,
                'timestamp': 1234567890,
                'txHash': tx_hash
            }
        }

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash)

        before_from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)

        self._engine._handle_score_invoke = \
            Mock(return_value=None, side_effect=RevertException("force revert"))
        self._engine._validate_score_blacklist = Mock()

        raise_exception_start_tag("test_score_invoke_with_revert")
        tx_results, state_root_hash = self._engine.invoke(block, [tx_v3])
        raise_exception_end_tag("test_score_invoke_with_revert")
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
        step_unit = self._engine._step_counter_factory.get_step_cost(
            StepType.DEFAULT)

        self.assertEqual(tx_result.step_used, step_unit)

        step_price = self._engine._get_step_price()
        if IconScoreContextUtil._is_flag_on(IconScoreContext.icon_service_flag, IconServiceFlag.fee):
            # step_price MUST BE 10**10 on protocol v2
            self.assertEqual(
                step_price, self._engine._step_counter_factory.get_step_price())
        else:
            self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        self._engine.commit(block)

        # Check whether fee charging works well
        after_from_balance: int = \
            self._engine._icx_engine.get_balance(None, self.from_)

        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(after_from_balance, before_from_balance - fee)

    def test_score_invoke_failure(self):
        tx_hash = create_tx_hash()
        method = 'icx_sendTransaction'
        params = {
            'from': self.from_,
            'to': self._icon_score_address,
            'value': 0,
            'fee': 10 ** 16,
            'timestamp': 1234567890,
            'txHash': tx_hash,
            'dataType': 'call',
            'data': {
                'method': 'transfer',
                'params': {
                    'to': self._to,
                    'value': 777
                }
            }
        }

        context = _create_context(IconScoreContextType.INVOKE)
        context.tx = Transaction(tx_hash=params['txHash'],
                                 origin=params['from'],
                                 index=0,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))
        context.block = Mock(spec=Block)
        context.msg = Message(sender=params['from'], value=params['value'])
        context.cumulative_step_used = Mock(spec=int)
        context.cumulative_step_used.attach_mock(Mock(), '__add__')
        context.step_counter = Mock(spec=IconScoreStepCounter)
        context.event_logs = []
        context.traces = Mock(spec=list)

        raise_exception_start_tag("test_score_invoke_failure")
        tx_result = self._engine._call(context, method, params)
        raise_exception_end_tag("test_score_invoke_failure")
        self.assertTrue(isinstance(tx_result, TransactionResult))
        self.assertEqual(TransactionResult.FAILURE, tx_result.status)
        self.assertEqual(self._icon_score_address, tx_result.to)
        self.assertEqual(tx_hash, tx_result.tx_hash)
        self.assertIsNone(tx_result.score_address)
        context.traces.append.assert_called()

        context_factory.destroy(context)

    def test_score_invoke_failure_by_readonly_external_call(self):
        block_height = 1
        block_hash = create_block_hash()
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 0
        to = self._governance_score_address

        step_limit = 200000000
        tx_v3 = {
            'method': 'icx_sendTransaction',
            'params': {
                'txHash': tx_hash,
                'nid': 3,
                'version': 3,
                'from': self._genesis_address,
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

        block = Block(block_height,
                      block_hash,
                      block_timestamp,
                      self.genesis_block.hash)

        tx_results, state_root_hash = self._engine.invoke(block, [tx_v3])
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
            prev_hash=create_block_hash())

        with self.assertRaises(ServerErrorException) as cm:
            self._engine.commit(block)
        e = cm.exception
        self.assertEqual(ExceptionCode.SERVER_ERROR, e.code)
        self.assertTrue(e.message.startswith('No precommit data'))

    def test_rollback(self):
        block = Block(
            block_height=1,
            block_hash=create_block_hash(),
            timestamp=0,
            prev_hash=self.genesis_block.hash)

        block_result, state_root_hash = self._engine.invoke(block, [])
        self.assertIsInstance(block_result, list)
        self.assertEqual(state_root_hash, hashlib.sha3_256(b'').digest())

        self._engine.rollback(block)
        self.assertIsNone(self._engine._precommit_data_manager.get(block))

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
                        'from': str(self.from_),
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

        tx_results, state_root_hash = self._engine.invoke(block, transactions)
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

        step_price = self._engine._get_step_price()
        self.assertEqual(tx_result.step_price, step_price)

        # Write updated states to levelDB
        self._engine.commit(block)

        # Check whether fee charging works well
        from_balance: int = self._engine._icx_engine.get_balance(
            None, self.from_)
        to_balance: int = self._engine._icx_engine.get_balance(None, to_address)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(0, fee)
        self.assertEqual(value, to_balance)
        self.assertEqual(from_balance, self._total_supply - value - fee)

    def test_get_balance_with_malformed_address_and_type_converter(self):
        empty_address = MalformedAddress.from_string('')
        short_address_without_hx = MalformedAddress.from_string('12341234')
        short_address = MalformedAddress.from_string('hx1234512345')
        long_address_without_hx = MalformedAddress.from_string(
            'cf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf')
        long_address = MalformedAddress.from_string(
            'hxdf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf')
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

            balance: int = self._engine.query(
                converted_request['method'], converted_request['params'])
            self.assertEqual(0, balance)


if __name__ == '__main__':
    unittest.main()
