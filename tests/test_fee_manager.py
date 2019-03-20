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
from iconservice.database.db import ContextDatabase
from iconservice.fee.fee_manager import FeeManager
from iconservice.iconscore.icon_score_context import ContextContainer
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
        icx_storage = IcxStorage(create_context_db())

        self._icx_engine = IcxEngine()
        self._icx_engine.open(icx_storage)

        self._sender_address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        self._icx_engine.init_account(
            None, AccountType.GENERAL, 'sender', self._sender_address, 1000000 * 10 ** 18)

        self._manager = FeeManager(icx_storage, self._icx_engine)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def test_set_fee_sharing_info(self):
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        ratio = 50

        self._manager.set_fee_sharing_ratio(score_address, ratio)

        score_fee_info = self._manager.get_score_fee_info(score_address)

        self.assertEqual(ratio, score_fee_info.sharing_ratio)

    def test_deposit_fee(self):
        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)
        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        self.assertEqual(amount, before_sender_balance - after_sender_balance)

        score_fee_info = self._manager.get_score_fee_info(score_address)

        self.assertEqual(1, len(score_fee_info.deposits))

        deposit = score_fee_info.deposits[0]
        self.assertEqual(tx_hash, deposit.id)
        self.assertEqual(score_address, deposit.score_address)
        self.assertEqual(self._sender_address, deposit.sender_address)
        self.assertEqual(amount, deposit.amount)
        self.assertEqual(block_number, deposit.created)
        self.assertEqual(block_number + period, deposit.expires)

    def test_withdraw_fee_without_penalty(self):
        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)
        self._manager.withdraw_fee(tx_hash, block_number + period + 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        score_fee_info = self._manager.get_score_fee_info(score_address)
        self.assertEqual(0, len(score_fee_info.deposits))
        self.assertEqual(amount, after_sender_balance - before_sender_balance)

    def test_withdraw_fee_with_penalty(self):
        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)
        self._manager.withdraw_fee(tx_hash, block_number + period - 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        score_fee_info = self._manager.get_score_fee_info(score_address)
        self.assertEqual(0, len(score_fee_info.deposits))
        self.assertGreater(0, after_sender_balance - before_sender_balance)
        self.assertLessEqual(amount, after_sender_balance - before_sender_balance)

    def test_get_deposit_info(self):
        tx_hash = os.urandom(32)
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        amount = 100 * 10 ** 18
        block_number = 1000
        period = 50

        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)
        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        self.assertEqual(amount, before_sender_balance - after_sender_balance)

        deposit = self._manager.get_deposit_info_by_id(tx_hash)

        self.assertEqual(tx_hash, deposit.id)
        self.assertEqual(score_address, deposit.score_address)
        self.assertEqual(self._sender_address, deposit.sender_address)
        self.assertEqual(amount, deposit.amount)
        self.assertEqual(block_number, deposit.created)
        self.assertEqual(block_number + period, deposit.expires)

    def test_get_available_step_with_sharing(self):
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        sender_step_limit = 10000

        ratio = 50
        self._manager.set_fee_sharing_ratio(score_address, ratio)

        available_step = self._manager.get_available_step(score_address, sender_step_limit)
        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(total_step - sender_step_limit, available_step.receiver_step)
        self.assertEqual(sender_step_limit, available_step.sender_step)

        ratio = 30
        self._manager.set_fee_sharing_ratio(score_address, ratio)

        available_step = self._manager.get_available_step(score_address, sender_step_limit)
        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(total_step - sender_step_limit, available_step.receiver_step)
        self.assertEqual(sender_step_limit, available_step.sender_step)

    def test_get_available_step_without_sharing(self):
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        sender_step_limit = 10000

        available_step = self._manager.get_available_step(score_address, sender_step_limit)
        self.assertEqual(0, available_step.receiver_step)
        self.assertEqual(sender_step_limit, available_step.sender_step)

    def test_charge_transaction_fee_without_sharing(self):
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = 1000 * 10 ** 18
        block_number = 1000
        period = 50
        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        self._manager.charge_transaction_fee(
            self._sender_address, score_address, step_price, used_step)

        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        self.assertEqual(step_price * used_step, before_sender_balance - after_sender_balance)

    def test_charge_transaction_fee_sharing_deposit(self):
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = 1000 * 10 ** 18
        block_number = 1000
        period = 50
        self._manager.deposit_fee(
            tx_hash, score_address, self._sender_address, amount, block_number, period)

        ratio = 50
        self._manager.set_fee_sharing_ratio(score_address, ratio)

        before_score_balance = self._icx_engine.get_balance(None, score_address)
        before_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        self._manager.charge_transaction_fee(
            self._sender_address, score_address, step_price, used_step)

        after_score_balance = self._icx_engine.get_balance(None, score_address)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender_address)

        score_charging_step = used_step * ratio / 100
        sender_charging_step = used_step - score_charging_step
        self.assertEqual(
            step_price * score_charging_step, before_score_balance - after_score_balance)
        self.assertEqual(
            step_price * sender_charging_step, before_sender_balance - after_sender_balance)

    # TODO test_charge_transaction_fee_sharing_virtual_step
    # TODO test_charge_transaction_fee_sharing_deposit_virtual_step
