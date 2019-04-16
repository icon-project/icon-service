# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

import os
import unittest
from random import randrange
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.block import Block
from iconservice.base.exception import MethodNotFoundException, InvalidParamsException
from iconservice.fee.fee_engine import FeeEngine
from iconservice.icon_constant import IconScoreContextType, GOVERNANCE_ADDRESS
from iconservice.iconscore import system_call_handler
from iconservice.iconscore.icon_score_context import IconScoreContext


# noinspection PyUnresolvedReferences
class TestSystemCallHandler(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_system_call_with_args(self):
        block_height = randrange(0, 100000)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.fee_engine = Mock(spec=FeeEngine)
        context.block = Block(block_height, os.urandom(32), 0, os.urandom(32))

        from_ = GOVERNANCE_ADDRESS
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        args = (score_address,)
        system_call_handler.handle_system_call(
            context, from_, 0, 'getScoreDepositInfo', args, None)

        context.fee_engine.get_deposit_info.assert_called_with(context, score_address, block_height)

    def test_handle_system_call_with_kwargs(self):
        block_height = randrange(0, 100000)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.fee_engine = Mock(spec=FeeEngine)
        context.block = Block(block_height, os.urandom(32), 0, os.urandom(32))

        from_ = GOVERNANCE_ADDRESS
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        args = {'address': score_address}
        system_call_handler.handle_system_call(
            context, from_, 0, 'getScoreDepositInfo', None, args)

        context.fee_engine.get_deposit_info.assert_called_with(context, score_address, block_height)

    def test_handle_system_call_with_invalid_args(self):
        block_height = randrange(0, 100000)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.fee_engine = Mock(spec=FeeEngine)
        context.block = Block(block_height, os.urandom(32), 0, os.urandom(32))

        from_ = GOVERNANCE_ADDRESS
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        args = (score_address, score_address)

        # noinspection PyTypeChecker
        with self.assertRaises(InvalidParamsException) as e:
            assert e is not None
            system_call_handler.handle_system_call(
                context, from_, 0, 'getScoreDepositInfo', args, None)

        context.fee_engine.get_deposit_info.assert_not_called()

    def test_handle_system_call_with_invalid_kwargs(self):
        block_height = randrange(0, 100000)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.fee_engine = Mock(spec=FeeEngine)
        context.block = Block(block_height, os.urandom(32), 0, os.urandom(32))

        from_ = GOVERNANCE_ADDRESS
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        args = {'address1': score_address}

        # noinspection PyTypeChecker
        with self.assertRaises(InvalidParamsException) as e:
            assert e is not None
            system_call_handler.handle_system_call(
                context, from_, 0, 'getScoreDepositInfo', None, args)

        context.fee_engine.get_deposit_info.assert_not_called()

    def test_handle_system_call_with_unknown_method(self):
        block_height = randrange(0, 100000)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.fee_engine = Mock(spec=FeeEngine)
        context.block = Block(block_height, os.urandom(32), 0, os.urandom(32))

        from_ = GOVERNANCE_ADDRESS
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        args = {'address': score_address}

        # noinspection PyTypeChecker
        with self.assertRaises(MethodNotFoundException) as e:
            assert e is not None
            system_call_handler.handle_system_call(
                context, from_, 0, 'getScoreDepositInfo1', None, args)

        context.fee_engine.get_deposit_info.assert_not_called()
