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

import unittest
from typing import List
from unittest.mock import Mock

from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_base import \
    IconScoreBase, InterfaceScore, external, interface, RevertException, \
    IconScoreException, ExceptionCode
from iconservice.iconscore.icon_score_context import \
    ContextContainer, IconScoreContext
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_trace import Trace, TraceType
from iconservice.icx import IcxEngine
from iconservice.utils import to_camel_case
from iconservice.utils.bloom import BloomFilter


class TestTrace(unittest.TestCase):

    def setUp(self):
        db = Mock(spec=IconScoreDatabase)
        address = Mock(spec=Address)
        context = Mock(spec=IconScoreContext)
        traces = Mock(spec=List[Trace])

        context.attach_mock(Mock(spec=Transaction), "tx")
        context.attach_mock(Mock(spec=Block), "block")
        context.attach_mock(Mock(spec=int), 'cumulative_step_used')
        context.cumulative_step_used.attach_mock(Mock(), '__add__')
        context.attach_mock(Mock(spec=IconScoreStepCounter), 'step_counter')
        context.attach_mock(Mock(spec=list), "event_logs")
        context.attach_mock(Mock(spec=BloomFilter), "logs_bloom")
        context.attach_mock(traces, 'traces')

        context.attach_mock(
            Mock(side_effect=RevertException('testRevert')), 'revert')

        ContextContainer._put_context(context)

        self._score = TestScore(db, address)

    def tearDown(self):
        self._mock_icon_score = None

    def test_transfer(self):
        context = ContextContainer._get_context()
        to_ = Mock(spec=Address)
        amount = 100
        self._score.icx.transfer(to_, amount)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.TRANSFER, trace.trace)
        self.assertEqual(to_, trace.data[0])
        self.assertEqual(amount, trace.data[1])

    def test_send(self):
        context = ContextContainer._get_context()
        to_ = Mock(spec=Address)
        amount = 100
        self._score.icx.send(to_, amount)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.TRANSFER, trace.trace)
        self.assertEqual(to_, trace.data[0])
        self.assertEqual(amount, trace.data[1])

    def test_call(self):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        func_name = "testCall"
        to_ = Mock(spec=Address)
        amount = 100
        params = {'to': to_, 'amount': amount}

        self._score.call(score_address, func_name, params)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.CALL, trace.trace)
        self.assertEqual(score_address, trace.data[0])
        self.assertEqual(func_name, trace.data[1])
        self.assertEqual(params['to'], trace.data[2][0])
        self.assertEqual(params['amount'], trace.data[2][1])

    def test_interface_call(self):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        to_ = Mock(spec=Address)
        amount = 100

        self._score.test_interface_call(score_address, to_, amount)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.CALL, trace.trace)
        self.assertEqual(score_address, trace.data[0])
        self.assertEqual('interfaceCall', trace.data[1])
        self.assertEqual(to_, trace.data[2][0])
        self.assertEqual(amount, trace.data[2][1])

    def test_revert(self):
        context = ContextContainer._get_context()

        self._icon_service_engine = IconServiceEngine()
        self._icon_service_engine._icx_engine = Mock(spec=IcxEngine)
        self._icon_service_engine._icon_score_deploy_engine = \
            Mock(spec=IconScoreDeployEngine)

        self._icon_service_engine._icon_score_engine = Mock(
            spec=IconScoreEngine)

        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)

        context.attach_mock(to_, "current_address")

        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        reason = Mock(spec=str)
        code = ExceptionCode.SCORE_ERROR
        mock_revert = Mock(side_effect=RevertException(reason))
        self._icon_service_engine._icon_score_engine.attach_mock(
            mock_revert, "invoke")

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            context, {'version': 3, 'from': from_, 'to': to_})
        self.assertEqual(0, tx_result.status)

        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.REVERT, trace.trace)
        self.assertEqual(to_, trace.score_address)
        self.assertEqual(code, trace.data[0])
        self.assertEqual(reason, trace.data[1])

    def test_throw(self):
        context = ContextContainer._get_context()

        self._icon_service_engine = IconServiceEngine()
        self._icon_service_engine._icx_engine = Mock(spec=IcxEngine)
        self._icon_service_engine._icon_score_deploy_engine = \
            Mock(spec=IconScoreDeployEngine)

        self._icon_service_engine._icon_score_engine = Mock(
            spec=IconScoreEngine)

        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)

        context.attach_mock(to_, "current_address")

        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        error = Mock(spec=str)
        code = ExceptionCode.SCORE_ERROR
        mock_exception = Mock(side_effect=IconScoreException(error, code))
        self._icon_service_engine._icon_score_engine.attach_mock(
            mock_exception, "invoke")

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            context, {'version': 3, 'from': from_, 'to': to_})
        self.assertEqual(0, tx_result.status)

        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        self.assertEqual(TraceType.THROW, trace.trace)
        self.assertEqual(to_, trace.score_address)
        self.assertEqual(code, trace.data[0])
        self.assertEqual(error, trace.data[1])

    def test_to_dict_camel(self):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        func_name = "testCall"
        to_ = Mock(spec=Address)
        amount = 100
        params = {'to': to_, 'amount': amount}

        self._score.call(score_address, func_name, params)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        camel_dict = trace.to_dict(to_camel_case)
        self.assertIn('scoreAddress', camel_dict)
        self.assertIn('trace', camel_dict)
        self.assertIn('data', camel_dict)
        self.assertEqual(TraceType.CALL.name, camel_dict['trace'])
        self.assertEqual(3, len(camel_dict['data']))


class TestInterfaceScore(InterfaceScore):
    @interface
    def interfaceCall(self, addr_to: Address, value: int) -> bool: pass


class TestScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase', owner: 'Address') -> None:
        super().__init__(db, owner)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def on_selfdestruct(self, recipient: 'Address') -> None:
        pass

    @external
    def test_interface_call(self,
                            score_address: Address, to_: Address, amount: int):
        test_interface_score = self.create_interface_score(
            score_address, TestInterfaceScore)
        test_interface_score.interfaceCall(to_, amount)
