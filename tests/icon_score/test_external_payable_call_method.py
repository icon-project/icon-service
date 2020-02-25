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

import unittest
from functools import wraps
from unittest.mock import Mock

import pytest

from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy import DeployEngine
from iconservice.icon_constant import IconScoreContextType, IconScoreFuncType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_base import IconScoreBase, external, payable
from iconservice.iconscore.icon_score_constant import ATTR_SCORE_CALL
from iconservice.iconscore.icon_score_context import IconScoreContext


def decorator(func):
    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


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


@pytest.fixture(scope="function")
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
    @pytest.mark.parametrize("context_type, func_type, func_name, msg_value, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.READONLY, "func1", 0, (), {}),
        (IconScoreContextType.QUERY, IconScoreFuncType.READONLY, "func1", 0, (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func2", 0, (), {"value": 1}),
        (IconScoreContextType.QUERY, IconScoreFuncType.WRITABLE, "func2", 0, (), {"value": 1}),
    ])
    def test_external_call(self, context, context_type, func_type, func_name, msg_value, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        context.msg.value = msg_value
        func(func_name, args, kwargs)

    @pytest.mark.parametrize("context_type, func_type, func_name, msg_value, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func1", 0, (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func1", 1, (), {}),
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func2", 0, (), {})
    ])
    def test_payable_call(self, context, context_type, func_type, func_name, msg_value, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        context.msg.value = msg_value
        func(func_name, args, kwargs)

    @pytest.mark.parametrize("context_type, func_type, func_name, msg_value, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func2", 1, (), {}),
    ])
    def test_payable_call_exception(self, context, context_type, func_type, func_name, msg_value, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        context.msg.value = msg_value
        with pytest.raises(BaseException) as e:
            func(func_name, args, kwargs)
        assert e.value.code == ExceptionCode.METHOD_NOT_PAYABLE
        assert e.value.message.startswith("Method not payable") is True

    @pytest.mark.parametrize("context_type, func_type, func_name, msg_value, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func1", 0, (), {}),
    ])
    def test_inherit_call(self, context, context_type, func_type, func_name, msg_value, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        test_score = ChildCallClass(Mock())

        context.msg.value = msg_value
        func = getattr(test_score, ATTR_SCORE_CALL)
        func(func_name, args, kwargs)

    @pytest.mark.parametrize("context_type, func_type, func_name, msg_value, args, kwargs", [
        (IconScoreContextType.INVOKE, IconScoreFuncType.WRITABLE, "func2", 0, (), {}),
    ])
    def test_inherit_call_exception(self, context, context_type, func_type, func_name, msg_value, args, kwargs):
        context.context_type = context_type
        context.func_type = func_type
        test_score = ChildCallClass(Mock())
        func = getattr(test_score, ATTR_SCORE_CALL)

        context.msg.value = msg_value
        with pytest.raises(BaseException) as e:
            func(func_name, args, kwargs)
        assert e.value.code == ExceptionCode.METHOD_NOT_FOUND
        assert e.value.message.startswith("Method not found") is True

