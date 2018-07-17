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
from typing import Optional
from unittest.mock import patch, MagicMock, Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.builtin_scores.governance.governance import STEP_TYPE_DEFAULT, \
    STEP_TYPE_CONTRACT_CALL, STEP_TYPE_CONTRACT_CREATE, \
    STEP_TYPE_CONTRACT_UPDATE, STEP_TYPE_CONTRACT_DESTRUCT, \
    STEP_TYPE_CONTRACT_SET, STEP_TYPE_SET, STEP_TYPE_REPLACE, STEP_TYPE_DELETE, \
    STEP_TYPE_INPUT, STEP_TYPE_EVENT_LOG
from iconservice.database.db import IconScoreDatabase
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_base import IconScoreBase, eventlog, \
    external
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContextFactory
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_step import StepType, \
    IconScoreStepCounter, IconScoreStepCounterFactory
from tests import create_block_hash, create_tx_hash, create_address


class TestIconScoreStepCounter(unittest.TestCase):

    @patch('iconservice.icon_service_engine.'
           'IconServiceEngine._init_global_value_by_governance_score')
    @patch('iconservice.icon_service_engine.'
           'IconServiceEngine._load_builtin_scores')
    @patch('iconservice.database.factory.DatabaseFactory.create_by_name')
    @patch('iconservice.icx.icx_engine.IcxEngine.open')
    def setUp(self, open, create_by_name, _load_builtin_scores,
              _init_global_value_by_governance_score):
        self._inner_task = IconScoreInnerTask(".", ".")
        open.assert_called()
        create_by_name.assert_called()
        _load_builtin_scores.assert_called()
        self._inner_task._icon_service_engine._icx_engine.get_balance = \
            Mock(return_value=100 * 10 ** 18)
        self._inner_task._icon_service_engine._icx_engine._transfer = Mock()
        self._inner_task._icon_service_engine.\
            _init_global_value_by_governance_score = \
            _init_global_value_by_governance_score

        factory = self._inner_task._icon_service_engine._step_counter_factory
        self.step_counter = Mock(spec=IconScoreStepCounter)
        factory.create = Mock(return_value=self.step_counter)
        self.step_counter.step_used = 0
        self.step_counter.step_price = 0
        self.step_counter.step_limit = 5000000

    def tearDown(self):
        self._inner_task = None

    @patch('iconservice.deploy.icon_score_deploy_engine.'
           'IconScoreDeployEngine.invoke')
    def test_install_step(self, invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = Address.from_string('cx0000000000000000000000000000000000000000')
        content_type = 'application/zip'
        data = {
            'contentType': content_type,
            'content': '0x1867291283973610982301923812873419826abcdef9182731',
        }
        req = self.get_request(tx_hash, to_, 'deploy', data)

        result = self._inner_task._invoke(req)
        invoke.assert_called()
        input_length = (len(content_type.encode('utf-8')) + 25)

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, input_length))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CREATE, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.CONTRACT_SET, 25))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 4)

    def test_transfer_step(self):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.EOA, b'eoa')
        req = self.get_request(tx_hash, to_, None, None)

        result = self._inner_task._invoke(req)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 2)

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_internal_transfer_step(self, invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.CONTRACT, b'score')
        req = self.get_request(tx_hash, to_, 'call', {})

        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(context_db))
            score.transfer()

        invoke.side_effect = intercept_invoke

        result = self._inner_task._invoke(req)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 4)

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_event_log_step(self, invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.CONTRACT, b'score')
        req = self.get_request(tx_hash, to_, 'call', {})

        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(context_db))
            address = create_address(AddressPrefix.EOA, b'address')
            i_data_param = b'i_data'
            data_param = b'data'
            text_param = 'text'
            score.SampleEvent(i_data_param, address, data_param, text_param)
            global event_log_data_size
            event_log_data_size = len(
                "SampleEvent(bytes,Address,bytes,str)".encode('utf-8')) + \
                                  len(i_data_param) + \
                                  len(address.body) + \
                                  len(data_param) + \
                                  len(text_param.encode('utf-8'))

        invoke.side_effect = intercept_invoke

        result = self._inner_task._invoke(req)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.EVENT_LOG, event_log_data_size))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 4)

    @staticmethod
    def get_request(tx_hash, to_, data_type, data):
        req = {
            'block': {
                'blockHash': bytes.hex(create_block_hash(b'block')),
                'blockHeight': hex(100),
                'timestamp': hex(1234),
                'prevBlockHash': bytes.hex(create_block_hash(b'prevBlock'))
            },
            'transactions': [{
                'method': 'icx_sendTransaction',
                'params': {
                    'txHash': tx_hash,
                    'version': hex(3),
                    'from': str(create_address(AddressPrefix.EOA, b'from')),
                    'to': str(to_),
                    'stepLimit': hex(5000000),
                    'timestamp': hex(123456),
                    'dataType': data_type,
                    'data': data,
                }
            }]
        }
        return req

    def test_set_step_costs(self):
        governance_score = Mock()
        governance_score.getStepCosts = Mock(return_value={
            STEP_TYPE_DEFAULT: 4000,
            STEP_TYPE_CONTRACT_CALL: 1500,
            STEP_TYPE_CONTRACT_CREATE: 20000,
            STEP_TYPE_CONTRACT_UPDATE: 8000,
            STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            STEP_TYPE_CONTRACT_SET: 1000,
            STEP_TYPE_SET: 20,
            STEP_TYPE_REPLACE: 5,
            STEP_TYPE_DELETE: -15,
            STEP_TYPE_INPUT: 20,
            STEP_TYPE_EVENT_LOG: 10
        })

        step_counter_factory = IconScoreStepCounterFactory()
        step_costs = governance_score.getStepCosts()

        for key, value in step_costs.items():
            step_counter_factory.set_step_cost(StepType(key), value)

        self.assertEqual(
            4000, step_counter_factory.get_step_cost(StepType.DEFAULT))
        self.assertEqual(
            1500, step_counter_factory.get_step_cost(StepType.CONTRACT_CALL))
        self.assertEqual(
            20000, step_counter_factory.get_step_cost(StepType.CONTRACT_CREATE))
        self.assertEqual(
            8000, step_counter_factory.get_step_cost(StepType.CONTRACT_UPDATE))
        self.assertEqual(
            -7000, step_counter_factory.get_step_cost(StepType.CONTRACT_DESTRUCT))
        self.assertEqual(
            1000, step_counter_factory.get_step_cost(StepType.CONTRACT_SET))
        self.assertEqual(
            20, step_counter_factory.get_step_cost(StepType.SET))
        self.assertEqual(
            5, step_counter_factory.get_step_cost(StepType.REPLACE))
        self.assertEqual(
            -15, step_counter_factory.get_step_cost(StepType.DELETE))
        self.assertEqual(
            20, step_counter_factory.get_step_cost(StepType.INPUT))
        self.assertEqual(
            10, step_counter_factory.get_step_cost(StepType.EVENT_LOG))


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
    def SampleEvent(
            self, i_data: bytes, address: Address, data: bytes, text: str):
        pass

    @external
    def transfer(self):
        self.icx.transfer(self.msg.sender, 10)

