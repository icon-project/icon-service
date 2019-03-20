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
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.exception import InvalidRequestException
from iconservice.database.db import ContextDatabase
from iconservice.deploy import DeployState
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployInfo
from iconservice.fee.fee_manager import FeeManager
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.icon_score_context import ContextContainer, IconScoreContext
from iconservice.icx import IcxEngine
from iconservice.icx.icx_account import AccountType
from iconservice.icx.icx_storage import IcxStorage
from tests.mock_generator import clear_inner_task


def create_context_db():
    """
    Create memory db for ContextDatabase

    :return: ContextDatabase
    """
    memory_db = {}

    # noinspection PyUnusedLocal
    def put(context, key, value):
        memory_db[key] = value

    # noinspection PyUnusedLocal
    def get(context, key):
        return memory_db.get(key)

    # noinspection PyUnusedLocal
    def delete(context, key):
        del memory_db[key]

    context_db = Mock(spec=ContextDatabase)
    context_db.get = get
    context_db.put = put
    context_db.delete = delete

    return context_db


class TestFeeManager(unittest.TestCase):

    def setUp(self):
        context = IconScoreContext(IconScoreContextType.DIRECT)

        self._sender = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        self._score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))

        context_db = create_context_db()

        deploy_storage = IconScoreDeployStorage(context_db)
        deploy_info = IconScoreDeployInfo(self._score_address,
                                          DeployState.ACTIVE,
                                          self._sender,
                                          os.urandom(32),
                                          os.urandom(32))
        icx_storage = IcxStorage(context_db)
        self._icx_engine = IcxEngine()

        deploy_storage.put_deploy_info(None, deploy_info)
        self._icx_engine.open(icx_storage)

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, 1000000 * 10 ** 18)

        self._manager = FeeManager(deploy_storage, icx_storage, self._icx_engine)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def test_set_fee_sharing_ratio(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        ratio = 50

        self._manager.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        score_fee_info = self._manager.get_score_fee_info(context, self._score_address)

        self.assertEqual(ratio, score_fee_info.sharing_ratio)

    def test_set_fee_sharing_ratio_invalid_request(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        # SCORE is not exists
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
            ratio = 50
            self._manager.set_fee_sharing_ratio(context, self._sender, score_address, ratio)

        # sender is not SCORE owner
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            sender = Address.from_data(AddressPrefix.EOA, os.urandom(20))
            ratio = 50
            self._manager.set_fee_sharing_ratio(context, sender, score_address, ratio)

        # negative ratio
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            ratio = -1
            self._manager.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        # ratio overflow
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            ratio = 101
            self._manager.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

    def test_deposit_fee(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._manager.deposit_fee(
            context, tx_hash, score_address, self._sender, amount, block_number, period)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self.assertEqual(amount, before_sender_balance - after_sender_balance)

        score_fee_info = self._manager.get_score_fee_info(context, score_address)

        self.assertEqual(1, len(score_fee_info.deposits))

        deposit = score_fee_info.deposits[0]
        self.assertEqual(tx_hash, deposit.id)
        self.assertEqual(self._sender, deposit.sender)
        self.assertEqual(score_address, deposit.score_address)
        self.assertEqual(amount, deposit.amount)
        self.assertEqual(block_number, deposit.created)
        self.assertEqual(block_number + period, deposit.expires)

    def test_withdraw_fee_without_penalty(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        self._manager.deposit_fee(
            context, tx_hash, self._sender, score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._manager.withdraw_fee(context, self._sender, tx_hash, block_number + period + 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_fee_info = self._manager.get_score_fee_info(context, score_address)
        self.assertEqual(0, len(score_fee_info.deposits))
        self.assertEqual(amount, after_sender_balance - before_sender_balance)

    def test_withdraw_fee_with_penalty(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        self._manager.deposit_fee(
            context, tx_hash, self._sender, score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._manager.withdraw_fee(context, self._sender, tx_hash, block_number + period - 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_fee_info = self._manager.get_score_fee_info(context, score_address)
        self.assertEqual(0, len(score_fee_info.deposits))
        self.assertGreater(0, after_sender_balance - before_sender_balance)
        self.assertLessEqual(amount, after_sender_balance - before_sender_balance)

    def test_get_deposit_info(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._manager.deposit_fee(
            context, tx_hash, self._sender, score_address, amount, block_number, period)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self.assertEqual(amount, before_sender_balance - after_sender_balance)

        deposit = self._manager.get_deposit_info_by_id(context, tx_hash)

        self.assertEqual(tx_hash, deposit.id)
        self.assertEqual(score_address, deposit.score_address)
        self.assertEqual(self._sender, deposit.sender_address)
        self.assertEqual(amount, deposit.amount)
        self.assertEqual(block_number, deposit.created)
        self.assertEqual(block_number + period, deposit.expires)

    def test_get_available_step_with_sharing(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        sender_step_limit = 10000

        ratio = 50
        self._manager.set_fee_sharing_ratio(context, self._sender, score_address, ratio)

        available_steps = self._manager.get_available_step(
            context, self._sender, score_address, sender_step_limit)
        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(total_step - sender_step_limit, available_steps.get(score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

        ratio = 30
        self._manager.set_fee_sharing_ratio(context, self._sender, score_address, ratio)

        available_steps = self._manager.get_available_step(
            context, self._sender, score_address, sender_step_limit)
        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(total_step - sender_step_limit, available_steps.get(score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

    def test_get_available_step_without_sharing(self):
        context = IconScoreContext(IconScoreContextType.QUERY)

        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        sender_step_limit = 10000

        available_steps = self._manager.get_available_step(
            context, self._sender, score_address, sender_step_limit)
        self.assertEqual(0, available_steps.get(score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

    def test_charge_transaction_fee_without_sharing(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = 1000 * 10 ** 18
        block_number = 1000
        period = 50
        self._manager.deposit_fee(
            context, tx_hash, self._sender, score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self._manager.charge_transaction_fee(
            context, self._sender, score_address, step_price, used_step)

        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self.assertEqual(step_price * used_step, before_sender_balance - after_sender_balance)

    def test_charge_transaction_fee_sharing_deposit(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = 1000 * 10 ** 18
        block_number = 1000
        period = 50
        self._manager.deposit_fee(
            context, tx_hash, self._sender, score_address, amount, block_number, period)

        ratio = 50
        self._manager.set_fee_sharing_ratio(context, self._sender, score_address, ratio)

        before_score_balance = self._icx_engine.get_balance(None, score_address)
        before_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self._manager.charge_transaction_fee(
            context, self._sender, score_address, step_price, used_step)

        after_score_balance = self._icx_engine.get_balance(None, score_address)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_charging_step = used_step * ratio / 100
        sender_charging_step = used_step - score_charging_step
        self.assertEqual(
            step_price * score_charging_step, before_score_balance - after_score_balance)
        self.assertEqual(
            step_price * sender_charging_step, before_sender_balance - after_sender_balance)

    # TODO test_charge_transaction_fee_sharing_virtual_step
    # TODO test_charge_transaction_fee_sharing_deposit_virtual_step
