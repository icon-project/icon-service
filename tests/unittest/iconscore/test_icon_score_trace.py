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
import os
from random import randrange
from unittest.mock import Mock, patch

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.block import Block
from iconservice.base.exception import (
    ExceptionCode,
    IconScoreException,
    InvalidParamsException,
)
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.batch import TransactionBatch
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy import DeployEngine, DeployStorage
from iconservice.icon_constant import IconScoreContextType
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_base import IconScoreBase, external, interface
from iconservice.iconscore.icon_score_base2 import InterfaceScore
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_trace import TraceType
from iconservice.iconscore.internal_call import InternalCall
from iconservice.icx import IcxEngine
from iconservice.utils import to_camel_case, ContextEngine, ContextStorage
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address


@pytest.fixture(scope="function")
def score_db():
    db = Mock(spec=IconScoreDatabase)
    db.address = create_address(AddressPrefix.CONTRACT)
    return db


@pytest.fixture(scope="function")
def context(score_db):
    context = IconScoreContext()
    context.icon_score_deploy_engine = Mock()
    traces = Mock(spec=list)

    context.tx = Mock(spec=Transaction)
    context.block = Mock(spec=Block)
    context.cumulative_step_used = Mock(spec=int)
    context.cumulative_step_used.attach_mock(Mock(), "__add__")
    context.step_counter = Mock(spec=IconScoreStepCounter)
    context.event_logs = []
    context.traces = traces
    context.tx_batch = TransactionBatch()
    IconScoreContext.engine = ContextEngine(
        icx=Mock(spec=IcxEngine), deploy=Mock(spec=DeployEngine)
    )
    IconScoreContext.storage = ContextStorage(deploy=Mock(spec=DeployStorage))
    context.icon_score_mapper = Mock()
    return context


@pytest.fixture(scope="function", autouse=True)
def set_container_and_intercall_before_test(monkeypatch, context):
    monkeypatch.setattr(InternalCall, "_other_score_call", Mock())
    ContextContainer._push_context(context)
    yield
    ContextContainer._clear_context()
    monkeypatch.undo()


@pytest.fixture(scope="function")
def mapped_test_score(score_db, context):
    context.icon_score_mapper.get_icon_score = Mock(return_value=TestScore(score_db))
    return TestScore(score_db)


class TestTrace:
    @pytest.mark.parametrize("func_name", ["send", "transfer"])
    def test_transfer_and_send_should_have_same_trace(
        self, mapped_test_score, func_name
    ):
        context = ContextContainer._get_context()
        context.type = IconScoreContextType.INVOKE
        to_ = create_address(AddressPrefix.EOA)
        amount = 100

        # Call send or transfer method
        func = getattr(mapped_test_score.icx, func_name)
        func(to_, amount)

        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        assert trace.trace == TraceType.CALL
        assert trace.data[0] == to_
        assert trace.data[3] == amount

    def test_call(self, mapped_test_score):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        func_name = "testCall"
        to_ = Mock(spec=Address)
        amount = 100
        params = {"to": to_, "amount": amount}

        mapped_test_score.call(score_address, func_name, params)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        assert trace.trace == TraceType.CALL
        assert trace.data[0] == score_address
        assert trace.data[1] == func_name
        assert trace.data[2][0] == params["to"]
        assert trace.data[2][1] == params["amount"]

    def test_interface_call(self, mapped_test_score):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        to_ = Mock(spec=Address)
        amount = 100

        mapped_test_score.test_interface_call(score_address, to_, amount)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]

        assert trace.trace == TraceType.CALL
        assert trace.data[0] == score_address
        assert trace.data[1] == "interfaceCall"
        assert trace.data[2][0] == to_
        assert trace.data[2][1] == amount

    def test_revert(self, mocker):
        mocker.patch.object(IconServiceEngine, "_charge_transaction_fee")
        mocker.patch.object(IconScoreEngine, "invoke")

        context = ContextContainer._get_context()

        icon_service_engine = IconServiceEngine()
        icon_service_engine._icx_engine = Mock(spec=IcxEngine)
        icon_service_engine._icon_score_deploy_engine = Mock(spec=DeployEngine)

        icon_service_engine._icon_pre_validator = Mock(spec=IconPreValidator)
        context.tx_batch = TransactionBatch()
        context.clear_batch = Mock()
        context.update_batch = Mock()

        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to_ = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        tx_index = randrange(0, 100)
        context.tx = Transaction(os.urandom(32), tx_index, from_, 0)
        context.msg = Message(from_)

        def intercept_charge_transaction_fee(*args, **kwargs):
            return {}, Mock(spec=int)

        IconServiceEngine._charge_transaction_fee.side_effect = (
            intercept_charge_transaction_fee
        )

        icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), "is_data_type_supported"
        )

        reason = Mock(spec=str)
        code = ExceptionCode.SCORE_ERROR
        mock_revert = Mock(side_effect=IconScoreException(reason))
        IconScoreEngine.invoke.side_effect = mock_revert

        raise_exception_start_tag("test_revert")
        tx_result = icon_service_engine._handle_icx_send_transaction(
            context, {"version": 3, "from": from_, "to": to_}
        )
        raise_exception_end_tag("test_revert")
        assert tx_result.status == 0

        IconServiceEngine._charge_transaction_fee.assert_called()
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        assert trace.trace == TraceType.REVERT
        assert trace.data[0] == code
        assert trace.data[1] == reason

    def test_throw(self, mocker):
        mocker.patch.object(IconServiceEngine, "_charge_transaction_fee")
        mocker.patch.object(IconScoreEngine, "invoke")
        context = ContextContainer._get_context()

        icon_service_engine = IconServiceEngine()
        icon_service_engine._icx_engine = Mock(spec=IcxEngine)
        icon_service_engine._icon_score_deploy_engine = Mock(spec=DeployEngine)
        icon_service_engine._icon_pre_validator = Mock(spec=IconPreValidator)
        context.tx_batch = TransactionBatch()
        context.clear_batch = Mock()
        context.update_batch = Mock()

        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to_ = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        tx_index = randrange(0, 100)
        context.tx = Transaction(os.urandom(32), tx_index, from_, 0)
        context.msg = Message(from_)

        def intercept_charge_transaction_fee(*args, **kwargs):
            return {}, Mock(spec=int)

        IconServiceEngine._charge_transaction_fee.side_effect = (
            intercept_charge_transaction_fee
        )

        icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), "is_data_type_supported"
        )

        error = Mock(spec=str)
        code = ExceptionCode.INVALID_PARAMETER
        mock_exception = Mock(side_effect=InvalidParamsException(error))
        IconScoreEngine.invoke.side_effect = mock_exception

        raise_exception_start_tag("test_throw")
        tx_result = icon_service_engine._handle_icx_send_transaction(
            context, {"version": 3, "from": from_, "to": to_}
        )
        raise_exception_end_tag("test_throw")
        assert 0 == tx_result.status

        IconServiceEngine._charge_transaction_fee.assert_called()
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        assert TraceType.THROW == trace.trace
        assert code == trace.data[0]
        assert error == trace.data[1]

    def test_to_dict_camel(self, mapped_test_score):
        context = ContextContainer._get_context()
        score_address = Mock(spec=Address)
        func_name = "testCall"
        to_ = Mock(spec=Address)
        amount = 100
        params = {"to": to_, "amount": amount}

        mapped_test_score.call(score_address, func_name, params)
        context.traces.append.assert_called()
        trace = context.traces.append.call_args[0][0]
        camel_dict = trace.to_dict(to_camel_case)
        assert "scoreAddress" in camel_dict
        assert "trace" in camel_dict
        assert "data" in camel_dict
        assert TraceType.CALL.name == camel_dict["trace"]
        assert 4 == len(camel_dict["data"])


class TestInterfaceScore(InterfaceScore):
    @interface
    def interfaceCall(self, addr_to: Address, value: int) -> bool:
        pass


class TestScore(IconScoreBase):
    def __init__(self, db: "IconScoreDatabase") -> None:
        super().__init__(db)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    @external
    def test_interface_call(self, score_address: Address, to_: Address, amount: int):
        test_interface_score = self.create_interface_score(
            score_address, TestInterfaceScore
        )
        test_interface_score.interfaceCall(to_, amount)
