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
import shutil
import unittest
import logging

from iconservice.base.address import Address, AddressPrefix, ICX_ENGINE_ADDRESS
from iconservice.base.address import create_address
from iconservice.base.exception import ExceptionCode, IconException
from iconservice.base.transaction import Transaction
from iconservice.base.message import Message
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.utils import sha3_256


logging.basicConfig(level=logging.NOTSET)
context_factory = IconScoreContextFactory(max_size=1)


def _create_context(context_type: IconScoreContextType) -> IconScoreContext:
    context = context_factory.create(context_type)

    if context.type == IconScoreContextType.INVOKE:
        context.block_batch = BlockBatch()
        context.tx_batch = TransactionBatch()

    return context


class TestIconServiceEngine(unittest.TestCase):
    def setUp(self):
        self._state_db_root_path = 'dbs'
        self._icon_score_root_path = 'scores'

        try:
            shutil.rmtree(self._icon_score_root_path)
            shutil.rmtree(self._state_db_root_path)
        except:
            pass

        engine = IconServiceEngine()
        engine.open(icon_score_root_path=self._icon_score_root_path,
                    state_db_root_path=self._state_db_root_path)
        self._engine = engine

        self._genesis_address = create_address(
            AddressPrefix.EOA, b'genesis')
        self._treasury_address = create_address(
            AddressPrefix.EOA, b'treasury')

        self._tx_hash = sha3_256(b'tx_hash').hex()
        self._from = self._genesis_address
        self._to = create_address(AddressPrefix.EOA, b'to')
        self._icon_score_address = create_address(
            AddressPrefix.CONTRACT, b'score')
        self._total_supply = 100 * 10 ** 18

        self.__step_counter_factory \
            = IconScoreStepCounterFactory(10, 10, 10, 10)
        self._engine._step_counter_factory = self.__step_counter_factory
        self._engine._precommit_state = None

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
        self._engine.genesis_invoke(accounts)

    def tearDown(self):
        self._engine.close()
        shutil.rmtree(self._icon_score_root_path)
        shutil.rmtree(self._state_db_root_path)

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

        balance = self._engine.call(context, method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(self._total_supply, balance)

        context_factory.destroy(context)

    def test_call_in_invoke(self):
        context = _create_context(IconScoreContextType.INVOKE)

        _from = self._genesis_address
        _to = self._to
        value = 1 * 10 ** 18

        method = 'icx_sendTransaction'
        params = {
            'from': _from,
            'to': _to,
            'value': value,
            'fee': 10 ** 16,
            'timestamp': 1234567890,
            'txHash': '0x4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed'
        }

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=0,
                                 origin=_from,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))

        self._engine.call(context, method, params)

        tx_batch = context.tx_batch
        self.assertEqual(1, len(tx_batch))
        self.assertTrue(ICX_ENGINE_ADDRESS in tx_batch)

        icon_score_batch = tx_batch[ICX_ENGINE_ADDRESS]
        self.assertEqual(2, len(icon_score_batch))

        balance = int.from_bytes(
            icon_score_batch[_to.body][-32:], 'big')
        self.assertEqual(value, balance)

        balance = int.from_bytes(
            icon_score_batch[_from.body][-32:], 'big')
        self.assertEqual(self._total_supply - value, balance)

        context_factory.destroy(context)

    def test_invoke(self):
        block_height = 1
        block_hash = None
        block_timestamp = 0
        value = 1 * 10 ** 18

        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'from': self._genesis_address,
                'to': self._to,
                'value': value,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'txHash': '0x4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed',
            }
        }

        tx_results = self._engine.invoke(
            block_height, block_hash, block_timestamp, [tx])
        print(tx_results[0])

    def test_score_invoke_failure(self):
        method = 'icx_sendTransaction'
        params = {
            'from': self._from,
            'to': self._icon_score_address,
            'value': 1 * 10 ** 18,
            'fee': 10 ** 16,
            'timestamp': 1234567890,
            'txHash': self._tx_hash,
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
        context.msg = Message(sender=params['from'], value=params['value'])

        tx_result = self._engine.call(context, method, params)
        self.assertTrue(isinstance(tx_result, TransactionResult))
        self.assertEqual(TransactionResult.FAILURE, tx_result.status)
        self.assertEqual(self._icon_score_address, tx_result.to)
        self.assertEqual(self._tx_hash, tx_result.tx_hash)
        self.assertIsNone(tx_result.score_address)
        print(tx_result)

        context_factory.destroy(context)

    def test_commit(self):
        with self.assertRaises(IconException) as cm:
            self._engine.commit()
        e = cm.exception
        self.assertEqual(ExceptionCode.INTERNAL_ERROR, e.code)
        self.assertEqual('Precommit state is none on commit', e.message)

    def test_rollback(self):
        self._engine.rollback()
        self.assertIsNone(self._engine._precommit_state)
        self.assertEqual(0, len(self._engine._icon_score_engine._deferred_tasks))

    '''
    def test_score_invoke(self):
        method = 'icx_sendTransaction'
        params = {
            'from': self._from,
            'to': self._icon_score_address,
            'value': 0,
            'fee': 10 ** 16,
            'tx_hash': '0x4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed',
            'signature': 'VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=',
            'data': {
                'method': 'transfer',
                'params': {
                    'to': self._to,
                    'value': 777
                }
            }
        }

        ret = self._engine.call(method, params)
        self.assertTrue(ret)
    '''

    '''
    def test_score_query(self):
        method = 'icx_call'
        params = {
            'from': self._from,
            'to': self._icon_score_address,
            'value': 10 ** 18,
            'data': {
                'method': 'balance_of',
                'params': {
                    'address': self._from
                }
            }
        }

        balance = self._engine.call(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0, balance)
    '''


if __name__ == '__main__':
    unittest.main()