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
import hashlib
import unittest
from typing import Optional
from unittest.mock import Mock, MagicMock, patch

from iconservice import EventLog
from iconservice.base.address import Address, AddressPrefix
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import IconServiceBaseException
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.icon_inner_service import MakeResponse, IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_base import IconScoreBase, eventlog, \
    external
from iconservice.iconscore.icon_score_context import IconScoreContext, \
    ContextContainer
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.icx import IcxEngine
from iconservice.utils import to_camel_case
from iconservice.utils.bloom import BloomFilter
from iconservice.icon_config import Configure
from tests import create_block_hash, create_tx_hash, create_address


class TestTransactionResult(unittest.TestCase):
    def setUp(self):
        self._icon_service_engine = IconServiceEngine()
        self._icon_service_engine._flag = 0
        self._icon_service_engine._icx_engine = Mock(spec=IcxEngine)

        self._icon_service_engine._icon_score_deploy_engine = \
            Mock(spec=IconScoreDeployEngine)

        self._icon_service_engine._icon_score_engine = Mock(
            spec=IconScoreEngine)

        step_counter_factory = IconScoreStepCounterFactory()
        step_counter_factory.get_step_cost = MagicMock(return_value=6000)
        self._icon_service_engine._step_counter_factory = step_counter_factory
        self._icon_service_engine._icon_pre_validator = \
            Mock(spec=IconPreValidator)

        self._mock_context = Mock(spec=IconScoreContext)
        self._mock_context.attach_mock(Mock(spec=Transaction), "tx")
        self._mock_context.attach_mock(Mock(spec=Block), "block")
        self._mock_context.event_logs = []
        self._mock_context.logs_bloom = BloomFilter()
        self._mock_context.traces = []
        self._mock_context.attach_mock(Mock(spec=int), "cumulative_step_used")
        self._mock_context.cumulative_step_used.attach_mock(Mock(), "__add__")
        self._mock_context.step_counter = step_counter_factory.create(5000000)
        self._mock_context.attach_mock(Mock(spec=Address), "current_address")

    def tearDown(self):
        self._icon_service_engine = None
        self._mock_context = None

    @patch('iconservice.icon_service_engine.IconServiceEngine.'
           '_charge_transaction_fee')
    def test_tx_success(self, IconServiceEngine_charge_transaction_fee):
        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")
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

        def intercept_charge_transaction_fee(*args, **kwargs):
            return Mock(spec=int), Mock(spec=int)

        IconServiceEngine_charge_transaction_fee.side_effect = \
            intercept_charge_transaction_fee

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, params)

        IconServiceEngine_charge_transaction_fee.assert_called()
        self.assertEqual(1, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(to_, tx_result.to)
        self.assertIsNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('failure', camel_dict)
        self.assertNotIn('scoreAddress', camel_dict)

    @patch('iconservice.icon_service_engine.IconServiceEngine.'
           '_charge_transaction_fee')
    def test_tx_failure(self, IconServiceEngine_charge_transaction_fee):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        self._icon_service_engine._icon_score_engine. \
            attach_mock(Mock(side_effect=IconServiceBaseException("error")),
                        "invoke")

        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")

        def intercept_charge_transaction_fee(*args, **kwargs):
            return Mock(spec=int), Mock(spec=int)

        IconServiceEngine_charge_transaction_fee.side_effect = \
            intercept_charge_transaction_fee

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})

        IconServiceEngine_charge_transaction_fee.assert_called()
        self.assertEqual(0, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertIsNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('scoreAddress', camel_dict)

    @patch('iconservice.icon_service_engine.IconServiceEngine.'
           '_charge_transaction_fee')
    def test_install_result(self, IconServiceEngine_charge_transaction_fee):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=True), 'is_data_type_supported')

        from_ = Address.from_data(AddressPrefix.EOA, b'test')
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")
        self._mock_context.tx.timestamp = 0
        self._mock_context.tx.origin = from_
        self._mock_context.tx.nonce = None

        def intercept_charge_transaction_fee(*args, **kwargs):
            return Mock(spec=int), Mock(spec=int)

        IconServiceEngine_charge_transaction_fee.side_effect = \
            intercept_charge_transaction_fee

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

        IconServiceEngine_charge_transaction_fee.assert_called()
        self.assertEqual(1, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(ZERO_SCORE_ADDRESS, tx_result.to)
        self.assertIsNotNone(tx_result.score_address)
        camel_dict = tx_result.to_dict(to_camel_case)
        self.assertNotIn('failure', camel_dict)

    def test_sample_result(self):
        from_ = Address.from_data(AddressPrefix.EOA, b'from')
        to_ = Address.from_data(AddressPrefix.CONTRACT, b'to')
        self._mock_context.tx.index = 1234
        self._mock_context.tx.hash = hashlib.sha256(b'hash').digest()
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})

        tx_result.score_address = \
            Address.from_data(AddressPrefix.CONTRACT, b'score_address')
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
        tx_result.block = Block(123, hashlib.sha256(b'block').digest(), 1, None)

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

        converted_result = MakeResponse.convert_type(camel_dict)
        self.assertFalse(converted_result['txHash'].startswith('0x'))
        self.assertTrue(converted_result['blockHeight'].startswith('0x'))
        self.assertTrue(converted_result['txIndex'].startswith('0x'))
        self.assertTrue(converted_result['to'].startswith('cx'))
        self.assertTrue(converted_result['scoreAddress'].startswith('cx'))
        self.assertTrue(converted_result['stepUsed'].startswith('0x'))
        self.assertTrue(converted_result['logsBloom'].startswith('0x'))
        self.assertTrue(converted_result['status'].startswith('0x'))

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    @patch('iconservice.icon_service_engine.'
           'IconServiceEngine._init_global_value_by_governance_score')
    @patch('iconservice.icon_service_engine.'
           'IconServiceEngine._load_builtin_scores')
    @patch('iconservice.database.factory.DatabaseFactory.create_by_name')
    @patch('iconservice.icx.icx_engine.IcxEngine.open')
    def test_request(self, open, create_by_name, _load_builtin_scores,
                     _init_global_value_by_governance_score, invoke):

        inner_task = IconScoreInnerTask(Configure(""), ".", ".")
        open.assert_called()
        create_by_name.assert_called()
        _load_builtin_scores.assert_called()

        inner_task._icon_service_engine._icx_engine.get_balance = \
            Mock(return_value=100 * 10 ** 18)

        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = create_address(AddressPrefix.CONTRACT, b'score')

        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(context_db))
            address = create_address(AddressPrefix.EOA, b'address')
            score.SampleEvent(b'i_data', address, 10, b'data', 'text')

        invoke.side_effect = intercept_invoke

        request = self.create_req(from_, to_)
        response = inner_task._invoke(request)
        invoke.assert_called()

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

    @staticmethod
    def create_req(from_, to_):
        req = {
            'block': {
                'blockHash': bytes.hex(create_block_hash(b'block')),
                'blockHeight': hex(100),
                'timestamp': hex(1234),
                'prevBlockHash': bytes.hex(create_block_hash(b'prevBlock'))
            },
            'transactions': [
                {
                    'method': 'icx_sendTransaction',
                    'params': {
                        'txHash': bytes.hex(create_tx_hash(b'tx1')),
                        'version': hex(3),
                        'from': str(from_),
                        'to': str(to_),
                        'stepLimit': hex(12345),
                        'timestamp': hex(123456),
                        'dataType': 'call',
                        'data': {},
                    }
                },
                {
                    'method': 'icx_sendTransaction',
                    'params': {
                        'txHash': bytes.hex(create_tx_hash(b'tx2')),
                        'version': hex(3),
                        'from': str(from_),
                        'to': str(to_),
                        'stepLimit': hex(12345),
                        'timestamp': hex(123456),
                        'dataType': 'call',
                        'data': {},
                    }
                }]
        }
        return req


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