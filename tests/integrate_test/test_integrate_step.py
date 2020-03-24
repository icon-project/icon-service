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
from typing import Optional, List
from unittest import mock

from iconservice import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.icon_constant import ConfigKey, IconScoreContextType, Revision
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextFactory
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.icon_score_step import StepType
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateStep(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.STEP_TRACE_FLAG: True,
            ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}
        }

    def setUp(self):
        super().setUp()
        self.create_context = IconScoreContextFactory._create_context
        self.is_step_trace_on = IconScoreContextFactory._is_step_trace_on

    def tearDown(self):
        super().tearDown()
        IconScoreContextFactory._create_context = self.create_context
        IconScoreContextFactory._is_step_trace_on = self.is_step_trace_on

    def _deploy_score(self,
                      to_: Optional['Address'] = ZERO_SCORE_ADDRESS) -> tuple:

        tx = self.create_deploy_score_tx(score_root="",
                                         score_name="step_test_score",
                                         from_=self._accounts[0],
                                         to_=to_,
                                         pre_validation_enabled=False)

        prev_block, hash_list = self.make_and_req_block([tx])
        return prev_block, self.get_tx_results(hash_list)

    def _send_message_tx(self, message: bytes):
        tx = self.create_message_tx(from_=self._accounts[1],
                                    to_=self._accounts[0],
                                    data=message)
        prev_block, hash_list = self.make_and_req_block([tx])
        return prev_block, self.get_tx_results(hash_list)

    def _transfer_icx(self, value: int):
        tx = self.create_transfer_icx_tx(from_=self._admin,
                                         to_=self._accounts[0],
                                         value=value)
        prev_block, hash_list = self.make_and_req_block([tx])
        return prev_block, self.get_tx_results(hash_list)

    def test_install(self):
        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash

        self.assertEqual(True, context.step_trace_flag)

        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CREATE, steps[2][0])
        self.assertEqual(StepType.CONTRACT_SET, steps[3][0])

        self._write_precommit_state(prev_block)

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        # 2. accpt SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2 = tx_results[0].tx_hash

        steps = context.step_counter.step_tracer.steps
        index = 0
        self.assertEqual(StepType.DEFAULT, steps[index][0])
        index += 1
        self.assertEqual(StepType.INPUT, steps[index][0])
        index += 1
        self.assertEqual(StepType.CONTRACT_CALL, steps[index][0])
        index += 1

        for i in range(10):
            self.assertEqual(StepType.GET, steps[index][0])
            index += 1

        for i in range(3):
            self.assertEqual(StepType.SET, steps[index][0])
            index += 1

        self.assertEqual(StepType.EVENT_LOG, steps[index][0])
        index += 1

        for i in range(28):
            self.assertEqual(StepType.GET, steps[index][0])
            index += 1

    def test_send_message(self):
        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        data: bytes = b'test_length_25_test_lengt'
        prev_block, tx_results = self._send_message_tx(data)
        self.assertEqual(True, context.step_trace_flag)

        input_step = context.step_counter.get_step_cost(StepType.INPUT)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(input_step * len(data), steps[1][1])

        self._write_precommit_state(prev_block)

    def test_transfer(self):
        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        icx = 1
        prev_block, tx_results = self._transfer_icx(icx)
        self.assertEqual(True, context.step_trace_flag)

        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])

        self._write_precommit_state(prev_block)

    def test_on_set(self):
        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="set_value",
                        params={"value": hex(1)})

        self.assertEqual(True, context.step_trace_flag)

        set_step = context.step_counter.get_step_cost(StepType.SET)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CALL, steps[2][0])
        self.assertEqual(StepType.SET, steps[3][0])
        self.assertEqual(set_step * 1, steps[3][1])
        self.assertEqual(StepType.EVENT_LOG, steps[4][0])

    def test_on_update(self):
        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="set_value",
                        params={"value": hex(1)})

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="set_value",
                        params={"value": hex(1)})

        self.assertEqual(True, context.step_trace_flag)

        replace_step = context.step_counter.get_step_cost(StepType.REPLACE)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CALL, steps[2][0])
        self.assertEqual(StepType.REPLACE, steps[3][0])
        self.assertEqual(replace_step * 1, steps[3][1])
        self.assertEqual(StepType.EVENT_LOG, steps[4][0])

    def test_on_get(self):
        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        # mock context
        context = IconScoreContext(IconScoreContextType.QUERY)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)
        IconScoreContextFactory._is_step_trace_on = mock.Mock(return_value=True)

        self.query_score(from_=self._accounts[0],
                         to_=score_addr,
                         func_name="get_value")

        self.assertEqual(True, context.step_trace_flag)

        get_step = context.step_counter.get_step_cost(StepType.GET)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.CONTRACT_CALL, steps[0][0])
        self.assertEqual(StepType.GET, steps[1][0])

    def test_on_remove(self):
        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="set_value",
                        params={"value": hex(1)})

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="del_value")

        self.assertEqual(True, context.step_trace_flag)

        delete_step = context.step_counter.get_step_cost(StepType.DELETE)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CALL, steps[2][0])
        self.assertEqual(StepType.DELETE, steps[3][0])

    def test_sha256_invoke(self):
        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="hash_writable",
                        params={"data": b'data'.hex()})

        self.assertEqual(True, context.step_trace_flag)

        api_step = context.step_counter.get_step_cost(StepType.API_CALL)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CALL, steps[2][0])

    def test_sha256_invoke_revision3(self):
        self.update_governance_for_audit("0_0_4")
        self.set_revision(Revision.THREE.value)

        # 1. deploy (wait audit)
        prev_block, tx_results = self._deploy_score()
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr: 'Address' = tx_results[0].score_address
        self._write_precommit_state(prev_block)
        self.accept_score(tx_hash1)

        # mock context
        context = IconScoreContext(IconScoreContextType.INVOKE)
        IconScoreContextFactory._create_context = mock.Mock(return_value=context)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="hash_writable",
                        params={"data": b'data'.hex()})

        self.assertEqual(True, context.step_trace_flag)

        api_step = context.step_counter.get_step_cost(StepType.API_CALL)
        steps = context.step_counter.step_tracer.steps
        self.assertEqual(StepType.DEFAULT, steps[0][0])
        self.assertEqual(StepType.INPUT, steps[1][0])
        self.assertEqual(StepType.CONTRACT_CALL, steps[2][0])
        self.assertEqual(StepType.API_CALL, steps[3][0])

