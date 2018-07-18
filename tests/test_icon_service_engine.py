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

"""IconScoreEngine testcase
"""
import os
import unittest
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, ServerErrorException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.icon_constant import IconServiceFlag, ConfigKey
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import StepType
from iconservice.utils.bloom import BloomFilter
from iconservice.icon_config import default_icon_config
from icon_common.icon_config import IconConfig
from tests import create_block_hash, create_address, rmtree, create_tx_hash

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
        self._icon_score_root_path = '.score'

        rmtree(self._icon_score_root_path)
        rmtree(self._state_db_root_path)

        engine = IconServiceEngine()
        conf = IconConfig("", default_icon_config)
        conf.load({ConfigKey.ADMIN_ADDRESS: str(create_address(AddressPrefix.EOA, b'ADMIN')),
                   ConfigKey.ICON_SCORE_ROOT: self._icon_score_root_path,
                   ConfigKey.ICON_SCORE_STATE_DB_ROOT_PATH: self._state_db_root_path})
        engine.open(conf)
        self._engine = engine

        self._genesis_address = create_address(
            AddressPrefix.EOA, b'genesis')
        self._treasury_address = create_address(
            AddressPrefix.EOA, b'treasury')

        self._from = self._genesis_address
        self._to = create_address(AddressPrefix.EOA, b'to')
        self._icon_score_address = create_address(
            AddressPrefix.CONTRACT, b'score')
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

        block = Block(0, create_block_hash(b'block'), 0, None)
        tx = {'method': '',
              'params': {'txHash': create_tx_hash()},
              'genesisData': {'accounts': accounts}}
        tx_lists = [tx]

        self._engine.invoke(block, tx_lists)
        self._engine.commit()

    def tearDown(self):
        self._engine.close()
        rmtree(self._icon_score_root_path)
        rmtree(self._state_db_root_path)

    def test_query(self):
        method = 'icx_getBalance'
        params = {'address': self._from}

        balance = self._engine.query(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self._total_supply, balance)

    def test_call_in_query(self):
        context = context_factory.create(IconScoreContextType.QUERY)

        method = 'icx_getBalance'
        params = {'address': self._from}

        balance = self._engine._call(context, method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self._total_supply, balance)

        context_factory.destroy(context)

    def test_call_in_invoke(self):
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

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=0,
                                 origin=from_,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))

        context.block = Mock(spec=Block)
        context.cumulative_step_used = Mock(spec=int)
        context.cumulative_step_used.attach_mock(Mock(), '__add__')
        context.step_counter: IconScoreStepCounter = \
            self._engine._step_counter_factory.create(params.get('stepLimit', 0))
        self._engine._call(context, method, params)

        tx_batch = context.tx_batch
        self.assertEqual(1, len(tx_batch))
        self.assertTrue(ICX_ENGINE_ADDRESS in tx_batch)

        # from(genesis), to
        # no transfer to fee_treasury because fee charging is disabled
        icon_score_batch = tx_batch[ICX_ENGINE_ADDRESS]
        self.assertEqual(2, len(icon_score_batch))

        context_factory.destroy(context)

    def test_invoke_v2_without_fee(self):
        block_height = 1
        block_hash = create_block_hash(b'block')
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

        tx_v2 = {
            'method': 'icx_sendTransaction',
            'params': {
                'from': self._from,
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
                      create_block_hash(b'prev'))

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

        # step_used MUST BE 10000 on protocol v2
        self.assertEqual(tx_result.step_used, 10000)

        step_price = self._engine._get_step_price()
        # if self._engine._is_flag_on(IconServiceFlag.ENABLE_FEE):
        #     # step_used MUST BE 10**12 on protocol v2
        #     self.assertEqual(step_price, 10 ** 12)
        # else:
        #     self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        # Write updated states to levelDB
        self._engine.commit()

        # Check whether fee charging works well
        from_balance: int = self._engine._icx_engine.get_balance(
            None, self._from)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, self._total_supply - value - fee)

    def test_invoke_v3_without_fee(self):
        block_height = 1
        block_hash = create_block_hash(b'block')
        block_timestamp = 0
        tx_hash = create_tx_hash()
        value = 1 * 10 ** 18

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
                      create_block_hash(b'prev'))

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

        # step_used MUST BE 10000 on protocol v2
        step_unit = self._engine._step_counter_factory.get_step_cost(
            StepType.DEFAULT)

        self.assertEqual(tx_result.step_used, step_unit)

        step_price = self._engine._get_step_price()
        if self._engine._is_flag_on(IconServiceFlag.ENABLE_FEE):
            # step_used MUST BE 10**12 on protocol v2
            self.assertEqual(step_price, 10 ** 12)
        else:
            self.assertEqual(step_price, 0)
        self.assertEqual(tx_result.step_price, step_price)

        self._engine.commit()

        # Check whether fee charging works well
        from_balance: int = self._engine._icx_engine.get_balance(None, self._from)
        fee = tx_result.step_price * tx_result.step_used
        self.assertEqual(fee, 0)
        self.assertEqual(from_balance, self._total_supply - value - fee)

    def test_score_invoke_failure(self):
        tx_hash = create_tx_hash()
        method = 'icx_sendTransaction'
        params = {
            'from': self._from,
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
        context.event_logs = Mock(spec=list)
        context.logs_bloom = Mock(spec=BloomFilter)
        context.traces = Mock(spec=list)

        tx_result = self._engine._call(context, method, params)
        self.assertTrue(isinstance(tx_result, TransactionResult))
        self.assertEqual(TransactionResult.FAILURE, tx_result.status)
        self.assertEqual(self._icon_score_address, tx_result.to)
        self.assertEqual(tx_hash, tx_result.tx_hash)
        self.assertIsNone(tx_result.score_address)
        context.traces.append.assert_called()

        context_factory.destroy(context)

    def test_commit(self):
        with self.assertRaises(ServerErrorException) as cm:
            self._engine.commit()
        e = cm.exception
        self.assertEqual(ExceptionCode.SERVER_ERROR, e.code)
        self.assertEqual('Precommit state is none on commit', e.message)

    def test_rollback(self):
        self._engine.rollback()
        self.assertIsNone(self._engine._precommit_state)
        

if __name__ == '__main__':
    unittest.main()
