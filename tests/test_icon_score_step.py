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
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.builtin_scores.governance import governance
from iconservice.database.db import IconScoreDatabase
from iconservice.iconscore.icon_score_base import \
    IconScoreBase, eventlog, external
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_step import \
    StepType, IconScoreStepCounter, IconScoreStepCounterFactory
from tests import create_tx_hash, create_address
from tests.mock_generator import generate_inner_task, create_request, ReqData


class TestIconScoreStepCounter(unittest.TestCase):

    def setUp(self):
        self._inner_task = generate_inner_task()

        factory = self._inner_task._icon_service_engine._step_counter_factory
        self.step_counter = Mock(spec=IconScoreStepCounter)
        factory.create = Mock(return_value=self.step_counter)
        self.step_counter.step_used = 0
        self.step_counter.step_price = 0
        self.step_counter.step_limit = 5000000

    def tearDown(self):
        self._inner_task = None

    def test_install_step(self):
        # Ignores deploy
        deploy_engine_invoke = Mock()
        deploy_storage_get_deploy_info = Mock(return_value=None)
        self._inner_task._icon_service_engine. \
            _icon_score_deploy_engine.invoke = deploy_engine_invoke
        self._inner_task._icon_service_engine.\
            _icon_score_deploy_storage.get_deploy_info = deploy_storage_get_deploy_info

        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = Address.from_string('cx0000000000000000000000000000000000000000')
        content_type = 'application/zip'
        data = {
            'contentType': content_type,
            'content': '0x1867291283973610982301923812873419826abcdef9182731',
        }

        request = create_request([
            ReqData(tx_hash, from_, to_, 'deploy', data),
        ])

        result = self._inner_task._invoke(request)
        deploy_engine_invoke.assert_called()
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
        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = create_address(AddressPrefix.EOA, b'eoa')

        request = create_request([
            ReqData(tx_hash, from_, to_, None, None),
        ])

        result = self._inner_task._invoke(request)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 2)

    def test_internal_transfer_step(self):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = create_address(AddressPrefix.CONTRACT, b'score')

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.transfer()

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        result = self._inner_task._invoke(request)
        score_engine_invoke.assert_called()

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

    def test_event_log_step(self):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        from_ = create_address(AddressPrefix.EOA, b'from')
        to_ = create_address(AddressPrefix.CONTRACT, b'score')

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            address = create_address(AddressPrefix.EOA, b'address')
            score = SampleScore(IconScoreDatabase(address, context_db))
            i_data_param = b'i_data'
            data_param = b'data'
            text_param = 'text'
            score.SampleEvent(i_data_param, address, data_param, text_param)
            global event_log_data_size
            event_log_data_size = \
                len("SampleEvent(bytes,Address,bytes,str)".encode('utf-8')) + \
                len(i_data_param) + \
                len(address.body) + \
                len(data_param) + \
                len(text_param.encode('utf-8'))

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        result = self._inner_task._invoke(request)
        score_engine_invoke.assert_called()

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

    def test_set_step_costs(self):
        governance_score = Mock()
        governance_score.getStepCosts = Mock(return_value={
            governance.STEP_TYPE_DEFAULT: 4000,
            governance.STEP_TYPE_CONTRACT_CALL: 1500,
            governance.STEP_TYPE_CONTRACT_CREATE: 20000,
            governance.STEP_TYPE_CONTRACT_UPDATE: 8000,
            governance.STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            governance.STEP_TYPE_CONTRACT_SET: 1000,
            governance.STEP_TYPE_SET: 20,
            governance.STEP_TYPE_REPLACE: 5,
            governance.STEP_TYPE_DELETE: -15,
            governance.STEP_TYPE_INPUT: 20,
            governance.STEP_TYPE_EVENT_LOG: 10
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
            -7000,
            step_counter_factory.get_step_cost(StepType.CONTRACT_DESTRUCT))
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
    def SampleEvent(
            self, i_data: bytes, address: Address, data: bytes, text: str):
        pass

    @external
    def transfer(self):
        self.icx.transfer(self.msg.sender, 10)
