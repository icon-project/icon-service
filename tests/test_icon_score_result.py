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
import hashlib
import os
import unittest
from typing import Optional
from unittest.mock import Mock
from random import randrange

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import IconServiceBaseException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.base.type_converter import TypeConverter
from iconservice.database.batch import TransactionBatch
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.icon_constant import REVISION_3
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_base import IconScoreBase, eventlog, \
    external
from iconservice.iconscore.icon_score_context import IconScoreContext, \
    ContextContainer, IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_event_log import EventLog
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.utils import to_camel_case
from iconservice.utils.bloom import BloomFilter
from tests import create_tx_hash, create_address, \
    raise_exception_start_tag, raise_exception_end_tag
from tests.mock_generator import generate_service_engine, generate_inner_task, \
    create_request, ReqData, clear_inner_task


class TestTransactionResult(unittest.TestCase):
    def setUp(self):
        self._icon_service_engine = generate_service_engine()
        self._icon_service_engine._icon_score_deploy_engine = \
            Mock(spec=IconScoreDeployEngine)

        self._icon_service_engine._charge_transaction_fee = \
            Mock(return_value=({}, 0))

        step_counter_factory = IconScoreStepCounterFactory()
        step_counter_factory.get_step_cost = Mock(return_value=6000)
        self._icon_service_engine._step_counter_factory = step_counter_factory
        self._icon_service_engine._icon_pre_validator = \
            Mock(spec=IconPreValidator)

        self._mock_context = IconScoreContext(IconScoreContextType.INVOKE)
        self._mock_context.tx = Transaction()
        self._mock_context.msg = Message()
        self._mock_context.block = Mock(spec=Block)
        self._mock_context.event_logs = []
        self._mock_context.traces = []
        self._mock_context.step_counter = step_counter_factory.create(5000000)
        self._mock_context.current_address = Mock(spec=Address)
        self._mock_context.revision = 0

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def test_tx_success(self):
        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        tx_index = randrange(0, 100)
        self._mock_context.tx = Transaction(os.urandom(32), tx_index, from_, 0)
        self._mock_context.msg = Message(from_)
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        params = {
            'version': 3,
            'from': from_,
            'to': to_,
            'value': 0,
            'timestamp': 1234567890,
            'nonce': 1
        }
        self._icon_service_engine._process_transaction = Mock(return_value=None)

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, params)

        self._icon_service_engine._charge_transaction_fee.assert_called()
        self.assertEqual(1, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(to_, tx_result.to)
        self.assertIsNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('failure', camel_dict)
        self.assertNotIn('scoreAddress', camel_dict)

    def test_tx_failure(self):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')
        IconScoreEngine.invoke = Mock(side_effect=IconServiceBaseException("error"))

        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to_ = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        tx_index = randrange(0, 100)
        self._mock_context.tx = Transaction(os.urandom(32), tx_index, from_, 0)
        self._mock_context.msg = Message(from_)
        self._mock_context.tx_batch = TransactionBatch()

        raise_exception_start_tag("test_tx_failure")
        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})
        raise_exception_end_tag("test_tx_failure")

        self._icon_service_engine._charge_transaction_fee.assert_called()
        self.assertEqual(0, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertIsNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('scoreAddress', camel_dict)

    def test_install_result(self):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=True), 'is_data_type_supported')

        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        self._mock_context.tx = Transaction(os.urandom(32), 0, from_, 0)
        self._mock_context.msg = Message(from_)

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context,
            {
                'version': 3,
                'from': from_,
                'to': ZERO_SCORE_ADDRESS,
                'dataType': 'deploy',
                'timestamp': 0,
                'data': {
                    'contentType': 'application/tbears',
                    'content': '/home/haha'
                }
            }
        )

        self._icon_service_engine._charge_transaction_fee.assert_called()
        self.assertEqual(1, tx_result.status)
        self.assertEqual(0, tx_result.tx_index)
        self.assertEqual(ZERO_SCORE_ADDRESS, tx_result.to)
        self.assertIsNotNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('failure', camel_dict)

    def test_sample_result(self):
        from_ = Address.from_data(AddressPrefix.EOA, b'from')
        to_ = Address.from_data(AddressPrefix.CONTRACT, b'to')
        self._mock_context.tx = Transaction(os.urandom(32), 1234, from_, 0)
        self._mock_context.msg = Message(from_)

        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')
        self._icon_service_engine._process_transaction = Mock(return_value=to_)

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})

        tx_result.score_address = to_
        tx_result.event_logs = [
            EventLog(
                Address.from_data(AddressPrefix.CONTRACT, b'addr_to'),
                [b'indexed', Address.from_data(AddressPrefix.EOA, b'index')],
                [True, 1234, 'str', None, b'test']
            )
        ]
        tx_result.logs_bloom = BloomFilter()
        tx_result.logs_bloom.add(b'1')
        tx_result.logs_bloom.add(b'2')
        tx_result.logs_bloom.add(b'3')
        tx_result.block = Block(123, hashlib.sha3_256(b'block').digest(), 1, None)

        camel_dict = tx_result.to_dict(to_camel_case)

        self.assertIn('txHash', camel_dict)
        self.assertIn('blockHeight', camel_dict)
        self.assertIn('txIndex', camel_dict)
        self.assertIn('to', camel_dict)
        self.assertIn('scoreAddress', camel_dict)
        self.assertIn('stepUsed', camel_dict)
        self.assertIn('stepPrice', camel_dict)
        self.assertIn('eventLogs', camel_dict)
        self.assertIn('logsBloom', camel_dict)
        self.assertIn('status', camel_dict)
        self.assertEqual(1, len(camel_dict['eventLogs']))
        self.assertIn('scoreAddress', camel_dict['eventLogs'][0])
        self.assertIn('indexed', camel_dict['eventLogs'][0])
        self.assertIn('data', camel_dict['eventLogs'][0])
        self.assertEqual(256, len(camel_dict['logsBloom']))

        converted_result = TypeConverter.convert_type_reverse(camel_dict)
        self.assertFalse(converted_result['txHash'].startswith('0x'))
        self.assertTrue(converted_result['blockHeight'].startswith('0x'))
        self.assertTrue(converted_result['txIndex'].startswith('0x'))
        self.assertTrue(converted_result['to'].startswith('cx'))
        self.assertTrue(converted_result['scoreAddress'].startswith('cx'))
        self.assertTrue(converted_result['stepUsed'].startswith('0x'))
        self.assertTrue(converted_result['logsBloom'].startswith('0x'))
        self.assertTrue(converted_result['status'].startswith('0x'))

    def test_request(self):
        inner_task = generate_inner_task(REVISION_3)

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])

            context_db = inner_task._icon_service_engine._icx_context_db

            score_address = create_address(AddressPrefix.CONTRACT, b'address')
            score = SampleScore(IconScoreDatabase(score_address, context_db))

            address = create_address(AddressPrefix.EOA, b'address')
            score.SampleEvent(b'i_data', address, 10, b'data', 'text')

            ContextContainer._pop_context()

        IconScoreEngine.invoke = Mock(side_effect=intercept_invoke)

        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = create_address(AddressPrefix.CONTRACT, b'score')

        request = create_request([
            ReqData(bytes.hex(create_tx_hash(b'tx1')), from_, to_, 0, 'call', {}),
            ReqData(bytes.hex(create_tx_hash(b'tx2')), from_, to_, 0, 'call', {})
        ])
        response = inner_task._invoke(request)

        step_total = 0

        for tx_hash in response['txResults'].keys():
            result = response['txResults'][tx_hash]
            step_total += int(result['stepUsed'], 16)
            self.assertIn('status', result)
            self.assertIn('txHash', result)
            self.assertIn('txIndex', result)
            self.assertIn('blockHeight', result)
            self.assertIn('blockHash', result)
            self.assertIn('cumulativeStepUsed', result)
            self.assertIn('stepUsed', result)
            self.assertEqual(1, len(result['eventLogs']))
            self.assertEqual(step_total, int(result['cumulativeStepUsed'], 16))

        clear_inner_task()


# noinspection PyPep8Naming
class SampleScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def get_owner(self,
                  score_address: Optional['Address']) -> Optional['Address']:
        return None

    @eventlog(indexed=2)
    def SampleEvent(self, i_data: bytes, address: Address, amount: int,
                    data: bytes, text: str):
        pass

    @external
    def empty(self):
        pass
