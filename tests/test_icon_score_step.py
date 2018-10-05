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
from typing import Optional
from unittest.mock import Mock

from iconservice import VarDB
from iconservice.base.address import AddressPrefix, Address
from iconservice.builtin_scores.governance import governance
from iconservice.database.db import IconScoreDatabase
from iconservice.iconscore.icon_score_base import \
    IconScoreBase, eventlog, external
from iconservice.iconscore.icon_score_base2 import sha3_256
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_step import \
    StepType, IconScoreStepCounter, IconScoreStepCounterFactory
from tests import create_tx_hash, create_address
from tests.mock_generator import generate_inner_task, create_request, ReqData, clear_inner_task


class TestIconScoreStepCounter(unittest.TestCase):

    def setUp(self):
        self._inner_task = generate_inner_task()

        factory = self._inner_task._icon_service_engine._step_counter_factory
        self.step_counter = Mock(spec=IconScoreStepCounter)
        factory.create = Mock(return_value=self.step_counter)
        self.step_counter.step_used = 0
        self.step_counter.step_price = 0
        self.step_counter.step_limit = 5000000
        self.step_cost_dict = self._init_step_cost()

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def test_install_step(self):
        # Ignores deploy
        deploy_engine_invoke = Mock()
        deploy_storage_get_deploy_info = Mock(return_value=None)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_deploy_engine.invoke = deploy_engine_invoke
        self._inner_task._icon_service_engine.\
            _icon_score_deploy_storage.get_deploy_info = deploy_storage_get_deploy_info

        tx_hash1 = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = Address.from_string('cx0000000000000000000000000000000000000000')
        content_type = 'application/zip'
        data = {
            'contentType': content_type,
            'content': '0x1867291283973610982301923812873419826abcdef9182731',
        }

        request1 = create_request([
            ReqData(tx_hash1, from_, to_, 'deploy', data),
        ])

        # for StepType.CONTRACT_CREATE
        result = self._inner_task_invoke(request1)
        self.assertEqual(result['txResults'][tx_hash1]['status'], '0x1')

        # for StepType.CONTRACT_UPDATE
        to_ = result['txResults'][tx_hash1]['scoreAddress']
        tx_hash2 = bytes.hex(create_tx_hash())

        request2 = create_request([
            ReqData(tx_hash2, from_, to_, 'deploy', data),
        ])

        result = self._inner_task_invoke(request2)
        self.assertEqual(result['txResults'][tx_hash2]['status'], '0x1')

        deploy_engine_invoke.assert_called()

        input_length = (len(content_type.encode('utf-8')) + 25)

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, input_length))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CREATE, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.CONTRACT_SET, 25))
        self.assertEqual(self.step_counter.apply_step.call_args_list[4][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[5][0],
                         (StepType.INPUT, input_length))
        self.assertEqual(self.step_counter.apply_step.call_args_list[6][0],
                         (StepType.CONTRACT_UPDATE, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[7][0],
                         (StepType.CONTRACT_SET, 25))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 8)

        step_used_create = self._calc_step_used(0, 4)
        step_used_update = self._calc_step_used(4, 4)

        # check SCORE install stepUsed value
        self._assert_step_used(step_used_create, request1, tx_hash1)

        # check SCORE update stepUsed value
        self._assert_step_used(step_used_update, request2, tx_hash2)

    def test_transfer_step(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.EOA)

        request = create_request([
            ReqData(tx_hash, from_, to_, "", ""),
        ])

        result = self._inner_task_invoke(request)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 2)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_internal_transfer_step(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.transfer()

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        score_engine_invoke.assert_called()

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        call_args_list = self.step_counter.apply_step.call_args_list
        self.assertEqual(call_args_list[0][0], (StepType.DEFAULT, 1))
        self.assertEqual(call_args_list[1][0], (StepType.INPUT, 0))
        self.assertEqual(call_args_list[2][0], (StepType.CONTRACT_CALL, 1))
        self.assertEqual(call_args_list[3][0], (StepType.CONTRACT_CALL, 1))
        self.assertEqual(len(call_args_list), 4)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_set_db(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.set_db(100)

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        # for StepType.SET
        result = self._inner_task_invoke(request)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')
        # for StepType.REPLACE
        result = self._inner_task_invoke(request)
        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')
        score_engine_invoke.assert_called()

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.SET, 100))
        self.assertEqual(self.step_counter.apply_step.call_args_list[4][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[5][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[6][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[7][0],
                         (StepType.REPLACE, 100))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 8)

        step_used_replace = self._calc_step_used(4, 4)

        # check stepUsed value
        self._assert_step_used(step_used_replace, request, tx_hash)

    def test_get_db(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        self._inner_task._icon_service_engine.\
            _icx_context_db.get = Mock(return_value=b'1' * 100)

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.get_db()

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        score_engine_invoke.assert_called()

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.GET, 100))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 4)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_query_db(self):
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = {
            'method': 'icx_call',
            'params': {
                'to': to_.__str__(),
                'from': from_.__str__(),
            },
        }

        self._inner_task._icon_service_engine. \
            _icx_context_db.get = Mock(return_value=b'1' * 100)

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            return score.query_db()

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.query = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task._query(request)
        score_engine_invoke.assert_called()

        self.assertIsNotNone(result)

        args_list = self.step_counter.apply_step.call_args_list
        self.assertEqual(args_list[0][0],(StepType.CONTRACT_CALL, 1))
        self.assertEqual(args_list[1][0],(StepType.GET, 100))

    def test_remove_db(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        self._inner_task._icon_service_engine.\
            _icx_context_db.get = Mock(return_value=b'1' * 100)

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.remove_db()

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        score_engine_invoke.assert_called()

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        self.assertEqual(self.step_counter.apply_step.call_args_list[0][0],
                         (StepType.DEFAULT, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[1][0],
                         (StepType.INPUT, 0))
        self.assertEqual(self.step_counter.apply_step.call_args_list[2][0],
                         (StepType.CONTRACT_CALL, 1))
        self.assertEqual(self.step_counter.apply_step.call_args_list[3][0],
                         (StepType.DELETE, 100))
        self.assertEqual(len(self.step_counter.apply_step.call_args_list), 4)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_event_log_step(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            address = create_address(AddressPrefix.EOA)
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

        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()

        result = self._inner_task_invoke(request)
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

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_hash_readonly(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        data_to_hash = b'1234'

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.hash_readonly(data_to_hash)

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        score_engine_invoke.assert_called()

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        call_args_list = self.step_counter.apply_step.call_args_list
        self.assertEqual(call_args_list[0][0], (StepType.DEFAULT, 1))
        self.assertEqual(call_args_list[1][0], (StepType.INPUT, 0))
        self.assertEqual(call_args_list[2][0], (StepType.CONTRACT_CALL, 1))
        self.assertEqual(call_args_list[3][0], (StepType.API_CALL, 1 + len(data_to_hash)))
        self.assertEqual(len(call_args_list), 4)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_hash_writable(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        data_to_hash = b'1234'

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.hash_writable(data_to_hash)

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        score_engine_invoke.assert_called()

        self.assertEqual(result['txResults'][tx_hash]['status'], '0x1')

        call_args_list = self.step_counter.apply_step.call_args_list
        self.assertEqual(call_args_list[0][0], (StepType.DEFAULT, 1))
        self.assertEqual(call_args_list[1][0], (StepType.INPUT, 0))
        self.assertEqual(call_args_list[2][0], (StepType.CONTRACT_CALL, 1))
        self.assertEqual(call_args_list[3][0], (StepType.API_CALL, 1 + len(data_to_hash)))
        self.assertEqual(len(call_args_list), 4)

        step_used = self._calc_step_used(0, len(self.step_counter.apply_step.call_args_list))

        # check stepUsed value
        self._assert_step_used(step_used, request, tx_hash)

    def test_out_of_step(self):
        tx_hash = bytes.hex(create_tx_hash())
        from_ = create_address(AddressPrefix.EOA)
        to_ = create_address(AddressPrefix.CONTRACT)

        request = create_request([
            ReqData(tx_hash, from_, to_, 'call', {})
        ])

        # noinspection PyUnusedLocal
        def intercept_invoke(*args, **kwargs):
            ContextContainer._push_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(to_, context_db))
            score.hash_writable(b'1234')

        score_engine_invoke = Mock(side_effect=intercept_invoke)
        self._inner_task._icon_service_engine._validate_score_blacklist = Mock()
        self._inner_task._icon_service_engine. \
            _icon_score_engine.invoke = score_engine_invoke

        raw_step_costs = {
            governance.STEP_TYPE_DEFAULT: 4000,
            governance.STEP_TYPE_CONTRACT_CALL: 1500,
            governance.STEP_TYPE_CONTRACT_CREATE: 20000,
            governance.STEP_TYPE_CONTRACT_UPDATE: 8000,
            governance.STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            governance.STEP_TYPE_CONTRACT_SET: 1000,
            governance.STEP_TYPE_GET: 5,
            governance.STEP_TYPE_SET: 20,
            governance.STEP_TYPE_REPLACE: 5,
            governance.STEP_TYPE_DELETE: -15,
            governance.STEP_TYPE_INPUT: 20,
            governance.STEP_TYPE_EVENT_LOG: 10,
            governance.STEP_TYPE_API_CALL: 0
        }
        step_costs = {}

        for key, value in raw_step_costs.items():
            try:
                step_costs[StepType(key)] = value
            except ValueError:
                # Pass the unknown step type
                pass

        self.step_counter = IconScoreStepCounter(step_costs, 100, 0)
        factory = self._inner_task._icon_service_engine._step_counter_factory
        factory.create = Mock(return_value=self.step_counter)

        self._inner_task._icon_service_engine._icon_score_mapper.get_icon_score = Mock(return_value=None)
        result = self._inner_task_invoke(request)
        self.assertTrue(result['txResults'][tx_hash]['failure']['message'].startswith("Out of step"))

    def test_set_step_costs(self):
        governance_score = Mock()
        governance_score.getStepCosts = Mock(return_value={
            governance.STEP_TYPE_DEFAULT: 4000,
            governance.STEP_TYPE_CONTRACT_CALL: 1500,
            governance.STEP_TYPE_CONTRACT_CREATE: 20000,
            governance.STEP_TYPE_CONTRACT_UPDATE: 8000,
            governance.STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            governance.STEP_TYPE_CONTRACT_SET: 1000,
            governance.STEP_TYPE_GET: 5,
            governance.STEP_TYPE_SET: 20,
            governance.STEP_TYPE_REPLACE: 5,
            governance.STEP_TYPE_DELETE: -15,
            governance.STEP_TYPE_INPUT: 20,
            governance.STEP_TYPE_EVENT_LOG: 10
        })

        step_counter_factory = IconScoreStepCounterFactory()
        step_costs = governance_score.getStepCosts()

        for key, value in step_costs.items():
            try:
                step_counter_factory.set_step_cost(StepType(key), value)
            except ValueError:
                pass

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
            5, step_counter_factory.get_step_cost(StepType.GET))
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

    @staticmethod
    def _init_step_cost() -> dict:
        raw_step_costs = {
            governance.STEP_TYPE_DEFAULT: 4000,
            governance.STEP_TYPE_CONTRACT_CALL: 1500,
            governance.STEP_TYPE_CONTRACT_CREATE: 20000,
            governance.STEP_TYPE_CONTRACT_UPDATE: 8000,
            governance.STEP_TYPE_CONTRACT_DESTRUCT: -7000,
            governance.STEP_TYPE_CONTRACT_SET: 1000,
            governance.STEP_TYPE_GET: 5,
            governance.STEP_TYPE_SET: 20,
            governance.STEP_TYPE_REPLACE: 5,
            governance.STEP_TYPE_DELETE: -15,
            governance.STEP_TYPE_INPUT: 20,
            governance.STEP_TYPE_EVENT_LOG: 10,
            governance.STEP_TYPE_API_CALL: 0
        }
        step_costs = {}

        for key, value in raw_step_costs.items():
            try:
                step_costs[StepType(key)] = value
            except ValueError:
                # Pass the unknown step type
                pass

        # return IconScoreStepCounter(step_costs, 5000000, 0)
        return step_costs

    def _calc_step_used(self, offset: int, count: int):
        step_used : int = 0

        for i in range(offset, offset + count):
            (type, val) = self.step_counter.apply_step.call_args_list[i][0]
            step_used = step_used + self.step_cost_dict[type] * val

        return step_used

    def _assert_step_used(self, step_used: int, request: dict, tx_hash: bytes):
        self.step_counter = IconScoreStepCounter(self.step_cost_dict, 5000000, 0)
        factory = self._inner_task._icon_service_engine._step_counter_factory
        factory.create = Mock(return_value=self.step_counter)

        results = self._inner_task_invoke(request)
        result = results['txResults'][tx_hash]
        self.assertEqual(result['status'], '0x1')
        self.assertEqual(result['stepUsed'], hex(step_used))

    def _inner_task_invoke(self, request) -> dict:
        # Clear cached precommit data before calling inner_task._invoke
        self._inner_task._icon_service_engine._precommit_data_manager.clear()
        return self._inner_task._invoke(request)

# noinspection PyPep8Naming
class SampleScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)
        self._db_field = VarDB("field", db, value_type=int)

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

    @external
    def set_db(self, size: int):
        data = b'1' * size
        self._db_field.set(data)

    @external
    def get_db(self):
        get = self._db_field.get()

    @external(readonly=True)
    def query_db(self) -> bytes:
        get = self._db_field.get()
        return get

    @external
    def remove_db(self):
        self._db_field.remove()

    @external(readonly=True)
    def hash_readonly(self, data: bytes) -> bytes:
        return sha3_256(data)

    @external
    def hash_writable(self, data: bytes) -> bytes:
        return sha3_256(data)


