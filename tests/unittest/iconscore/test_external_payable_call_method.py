# -*- coding: utf-8 -*-
#
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

from unittest.mock import Mock

import pytest

from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, MethodNotFoundException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy import DeployEngine
from iconservice.icon_constant import IconScoreContextType, IconScoreFuncType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_base import IconScoreBase, external, payable
from iconservice.iconscore.icon_score_constant import ATTR_SCORE_CALL
from iconservice.iconscore.icon_score_context import IconScoreContext


class ExternalCallClass(IconScoreBase):
    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    @external(readonly=True)
    def func1(self) -> int:
        pass

    @external
    def func2(self, value: int) -> None:
        pass


class ExternalPayableCallClass(IconScoreBase):
    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    @external
    @payable
    def func1(self):
        pass

    @external
    def func2(self):
        pass


class BaseCallClass(IconScoreBase):
    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    def func1(self):
        pass

    @external
    def func2(self):
        pass


class ChildCallClass(BaseCallClass):
    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    @external
    def func1(self):
        pass

    def func2(self):
        pass


@pytest.fixture
def context():
    IconScoreContext.icon_score_deploy_engine = Mock(spec=DeployEngine)
    context = Mock(spec=IconScoreContext)
    context.attach_mock(Mock(spec=Transaction), "tx")
    context.attach_mock(Mock(spec=Block), "block")
    context.attach_mock(Mock(spec=Message), "msg")
    ContextContainer._push_context(context)
    yield context
    ContextContainer._pop_context()


class TestExternalPayableCall:

    @pytest.mark.parametrize("context_type, func_type, msg_value, func_name, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.READONLY, 0, "func1", (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, 0, "func2", (), {"value": 1}),
        (IconScoreContextType.QUERY, IconScoreFuncType.READONLY, 0, "func1", (), {}),
        (IconScoreContextType.QUERY, IconScoreFuncType.WRITABLE, 0, "func2", (), {"value": 1}),
    ])
    def test_external_call(self, context, context_type, func_type, msg_value, func_name, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        context.msg.value = msg_value
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        func(func_name, args, kwargs)

    @pytest.mark.parametrize("context_type, func_type, msg_value, func_name, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, 0, "func1", (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, 1, "func1", (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, 0, "func2", (), {})
    ])
    def test_payable_call(self, context, context_type, func_type, msg_value, func_name, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        context.msg.value = msg_value
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        func(func_name, args, kwargs)

    @pytest.mark.parametrize("context_type, func_type, msg_value, func_name, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, 1, "func2", (), {}),
    ])
    def test_call_with_value_to_not_payable_call_raise_exception(self,
                                                                 context, context_type, func_type, msg_value,
                                                                 func_name, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        context.msg.value = msg_value
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        with pytest.raises(BaseException) as e:
            func(func_name, args, kwargs)

        assert e.value.code == ExceptionCode.METHOD_NOT_PAYABLE
        assert e.value.message.startswith("Method not payable") is True

    @pytest.mark.parametrize("context_type", [context_type for context_type in IconScoreContextType])
    @pytest.mark.parametrize("func_type", [func_type for func_type in IconScoreFuncType])
    @pytest.mark.parametrize("msg_value, func_name, args, kwargs", [
        (0, "func1", (), {}),
        pytest.param(0, "func2", (), {},
                     marks=pytest.mark.xfail(raises=MethodNotFoundException, reason="Method does not exists"))
    ])
    def test_inherit_call_case(self,
                               context,
                               context_type,
                               func_type,
                               msg_value, func_name, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        context.msg.value = msg_value
        test_score = ChildCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        func(func_name, args, kwargs)
