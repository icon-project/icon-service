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
from unittest.mock import Mock

from functools import wraps

from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine

from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.iconscore.icon_score_base import IconScoreBase, external, payable
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreFuncType
from iconservice.iconscore.icon_score_context import Message, ContextContainer, IconScoreContext
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil


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


class TestExternalPayableCall(unittest.TestCase):

    def setUp(self):
        IconScoreContextUtil.icon_score_deploy_engine = Mock(spec=IconScoreDeployEngine)
        self.context = Mock(spec=IconScoreContext)
        self.context.attach_mock(Mock(spec=Transaction), "tx")
        self.context.attach_mock(Mock(spec=Block), "block")
        self.context.attach_mock(Mock(spec=Message), "msg")

        ContextContainer._push_context(self.context)

    def tearDown(self):
        ContextContainer._pop_context()

    def test_readonly_external_call1(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.READONLY
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func1', (), {})

    def test_readonly_external_call2(self):
        self.context.context_type = IconScoreContextType.QUERY
        self.context.func_type = IconScoreFuncType.READONLY
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func1', (), {})

    def test_writable_external_call1(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func2', (), {"value": 1})

    def test_writable_external_call2(self):
        self.context.context_type = IconScoreContextType.QUERY
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func2', (), {"value": 1})

    def test_payable_call1(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func1', (), {})

    def test_payable_call2(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 1
        func('func1', (), {})

    def test_payable_call3(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 0
        func('func2', (), {})

    def test_payable_call4(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ExternalPayableCallClass(Mock())
        func = getattr(test_score, '_IconScoreBase__external_call')

        self.context.msg.value = 1
        with self.assertRaises(BaseException) as e:
            func('func2', (), {})
        self.assertEqual(e.exception.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(e.exception.message, "This is not payable")

    def test_inherit_call1(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ChildCallClass(Mock())

        self.context.msg.value = 0
        func = getattr(test_score, '_IconScoreBase__external_call')
        func('func1', (), {})

    def test_inherit_call2(self):
        self.context.context_type = IconScoreContextType.INVOKE
        self.context.func_type = IconScoreFuncType.WRITABLE
        test_score = ChildCallClass(Mock())

        self.context.msg.value = 0
        func = getattr(test_score, '_IconScoreBase__external_call')
        with self.assertRaises(BaseException) as e:
            func('func2', (), {})
        self.assertEqual(e.exception.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertEqual(e.exception.message, "Invalid external method")
