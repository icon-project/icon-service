# -*- coding: utf-8 -*-
#
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
from functools import wraps
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix
from iconservice.base.block import Block
from iconservice.base.exception import ExternalException, PayableException, \
    IconScoreException
from iconservice.base.transaction import Transaction
from iconservice.database.db import IconScoreDatabase
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_manager import IconScoreManager
from iconservice.iconscore.icon_score_base import IconScoreBase, external, \
    payable
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreFuncType
from iconservice.iconscore.icon_score_context import Message, ContextContainer, \
    IconScoreContext
from tests import create_address
from tests.mock_db import create_mock_icon_score_db


def decorator(func):
    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        print('!!')
        res = func(calling_obj, *args, **kwargs)
        return res
    return __wrapper


class CallClass1(IconScoreBase):
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
    @decorator
    def func2(self, arg1: int, arg2: str):
        pass

    @payable
    @external
    def func3(self, arg1: int, arg2: str):
        pass

    @payable
    @external
    def func4(self, arg1: int, arg2: str):
        pass

    @payable
    def func5(self, arg1: int, arg2: str):
        pass

    def func6(self):
        pass

    @payable
    def fallback(self):
        pass


class CallClass2(CallClass1):
    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    def __init__(self, db: IconScoreDatabase):
        super().__init__(db)

    def func1(self) -> int:
        pass

    @payable
    @external
    def func5(self, arg1: int, arg2: str):
        pass

    def fallback(self):
        pass


class TestContextContainer(ContextContainer):
    pass


class TestCallMethod(unittest.TestCase):

    def setUp(self):
        self._mock_context = Mock(spec=IconScoreContext)
        self._mock_context.attach_mock(Mock(spec=Transaction), "tx")
        self._mock_context.attach_mock(Mock(spec=Block), "block")
        self._mock_context.attach_mock(Mock(spec=Message), "message")
        self._mock_icon_score_manager = Mock(spec=IconScoreManager)
        self._mock_icon_score_manager.attach_mock(Mock(spec=IconScoreDeployStorage), "icon_deploy_storage")

        self._context_container = TestContextContainer()
        self._context_container._put_context(self._mock_context)

    def tearDown(self):
        self.ins = None

    def test_success_call_method(self):
        self._mock_context.readonly = False
        self._mock_context.func_type = IconScoreFuncType.WRITABLE
        self.ins = CallClass2(create_mock_icon_score_db())
        self._mock_context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
        self._mock_context.type = IconScoreContextType.INVOKE
        func = getattr(self.ins, '_IconScoreBase__call_method')
        # func('func1', {})
        func('func2', (1, 2), {})
        self._mock_context.type = IconScoreContextType.QUERY
        # func('func3', {})
        self._mock_context.type = IconScoreContextType.INVOKE
        func('func4', (1, 2), {})
        func('func5', (1, 2), {})
        # func('func6', {})

        print(self.ins.get_api())

    # def test_fail_call_method(self):
    #     self._mock_context.readonly = False
    #     self._mock_context.func_type = IconScoreFuncType.WRITABLE
    #     self.ins = CallClass2(create_mock_icon_score_db())
    #     self._mock_context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 1)
    #     func = getattr(self.ins, '_IconScoreBase__call_method')
    #     self.assertRaises(ExternalException, func, 'func1', (1, 2), {})
    #     self.assertRaises(PayableException, func, 'func2', (1, 2), {})
    #     # self._context.type = IconScoreContextType.GENESIS
    #     # self.assertRaises(ExternalException, func, 'func3', {})
    #     self._mock_context.readonly = True
    #     self._mock_context.type = IconScoreContextType.QUERY
    #     self.assertRaises(IconScoreException, func, 'func4', (1, 2), {})
    #     self.assertRaises(IconScoreException, func, 'func5', (1, 2), {})
    #
    #     self.assertRaises(ExternalException, func, 'func6', (1, 2), {})
    #
    #     self._mock_context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
    #     # self.assertRaises(PayableException, func, 'func3', {})
    #     # self.assertRaises(PayableException, func, 'func4', {})
    #     # self.assertRaises(ExternalException, func, 'func5', {})
    #     self.assertRaises(ExternalException, func, 'func6', (1, 2), {})

    def test_func2_with_decorator(self):
        self._mock_context.readonly = False
        self._mock_context.func_type = IconScoreFuncType.WRITABLE
        self._mock_context.msg = Message(create_address(AddressPrefix.EOA, b'from'), 0)
        self.ins = CallClass2(create_mock_icon_score_db())
        func = getattr(self.ins, '_IconScoreBase__call_method')
        func('func2', (1, 2), {})


