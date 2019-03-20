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
from iconservice.base.exception import InvalidRequestException, InvalidParamsException
from iconservice.database.db import ContextDatabase
from iconservice.deploy import DeployState
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployInfo
from iconservice.fee.fee_engine import FeeEngine
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.icon_score_context import ContextContainer, IconScoreContext
from iconservice.icx import IcxEngine
from iconservice.icx.icx_account import AccountType, Account
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


def patch_icx_storage(icx_storage: IcxStorage):
    memory_db = {}

    # noinspection PyUnusedLocal
    def put(context, key, value):
        memory_db[key] = value

    # noinspection PyUnusedLocal
    def get(context, key):
        return memory_db[key] if key in memory_db else None

    # noinspection PyUnusedLocal
    def delete(context, key):
        del memory_db[key]

    icx_storage.put_score_fee = put
    icx_storage.get_score_fee = get
    icx_storage.delete_score_fee = delete
    icx_storage.put_deposit = put
    icx_storage.get_deposit = get
    icx_storage.delete_deposit = delete


class TestFeeEngine(unittest.TestCase):

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
        patch_icx_storage(icx_storage)
        self._icx_engine = IcxEngine()

        deploy_storage.put_deploy_info(context, deploy_info)
        self._icx_engine.open(icx_storage)

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, 100000000 * 10 ** 18)

        treasury = Account(
            AccountType.TREASURY, Address.from_data(AddressPrefix.EOA, os.urandom(20)))
        self._icx_engine._init_special_account(context, treasury)

        self._engine = FeeEngine(deploy_storage, icx_storage, self._icx_engine)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def test_set_fee_sharing_ratio(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        # Sets new ratio
        ratio = 50

        self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)
        sharing_ratio = self._engine.get_fee_sharing_ratio(context, self._score_address)
        self.assertEqual(ratio, sharing_ratio)

        # Modifies ratio
        ratio = 30

        self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)
        sharing_ratio = self._engine.get_fee_sharing_ratio(context, self._score_address)
        self.assertEqual(ratio, sharing_ratio)

    def test_set_fee_sharing_ratio_invalid_request(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        # SCORE is not exists
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
            ratio = 50
            self._engine.set_fee_sharing_ratio(context, self._sender, score_address, ratio)

        # sender is not SCORE owner
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            sender = Address.from_data(AddressPrefix.EOA, os.urandom(20))
            ratio = 50
            self._engine.set_fee_sharing_ratio(context, sender, score_address, ratio)

        # negative ratio
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            ratio = -1
            self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        # ratio overflow
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException):
            ratio = 101
            self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

    def test_deposit_fee(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        block_number = 0

        size = randrange(10, 100)
        input_param = []
        for i in range(size):
            tx_hash = os.urandom(32)
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            block_number = randrange(100, 10000)
            period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

            before_sender_balance = self._icx_engine.get_balance(None, self._sender)
            self._engine.deposit_fee(
                context, tx_hash, self._sender, self._score_address, amount, block_number, period)
            after_sender_balance = self._icx_engine.get_balance(None, self._sender)

            self.assertEqual(amount, before_sender_balance - after_sender_balance)
            input_param.append((tx_hash, amount, block_number, period))

        score_info = self._engine.get_score_fee_info(context, self._score_address, block_number)

        self.assertEqual(size, len(score_info.deposits))

        for i in range(size):
            tx_hash, amount, block_number, period = input_param[i]
            deposit = score_info.deposits[i]
            self.assertEqual(tx_hash, deposit.id)
            self.assertEqual(self._sender, deposit.sender)
            self.assertEqual(self._score_address, deposit.score_address)
            self.assertEqual(amount, deposit.deposit_amount)
            self.assertEqual(block_number, deposit.created)
            self.assertEqual(block_number + period, deposit.expires)

    def test_deposit_fee_invalid_param(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        # invalid amount (underflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_amount = randrange(0, FeeEngine._MIN_DEPOSIT_AMOUNT - 1)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     inv_amount, block_number, period)
        self.assertEqual('Invalid deposit amount', e.exception.message)

        # invalid amount (overflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_amount = \
                randrange(FeeEngine._MAX_DEPOSIT_AMOUNT + 1, FeeEngine._MAX_DEPOSIT_AMOUNT * 10)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     inv_amount, block_number, period)
        self.assertEqual('Invalid deposit amount', e.exception.message)

        # invalid period (underflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_period = randrange(0, FeeEngine._MIN_DEPOSIT_PERIOD - 1)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, inv_period)
        self.assertEqual('Invalid deposit period', e.exception.message)

        # invalid period (overflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_period = \
                randrange(FeeEngine._MAX_DEPOSIT_PERIOD + 1, FeeEngine._MAX_DEPOSIT_PERIOD * 10)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, inv_period)
        self.assertEqual('Invalid deposit period', e.exception.message)

        # invalid owner
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_sender = Address.from_data(AddressPrefix.EOA, os.urandom(20))
            self._engine.deposit_fee(context, tx_hash, inv_sender, self._score_address,
                                     amount, block_number, period)
        self.assertEqual('Invalid SCORE owner', e.exception.message)

    def test_deposit_fee_out_of_balance(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, 10000 * 10 ** 18)

        tx_hash = os.urandom(32)
        amount = 10001 * 10 ** 18
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        # out of balance
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidParamsException) as e:
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, period)
        self.assertEqual('Out of balance', e.exception.message)

    def test_withdraw_fee_without_penalty(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        self._engine.deposit_fee(
            context, tx_hash, self._sender, self._score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._engine.withdraw_fee(context, self._sender, tx_hash, block_number + period + 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_info = self._engine.get_score_fee_info(context, self._score_address, block_number)
        self.assertEqual(0, len(score_info.deposits))
        self.assertEqual(amount, after_sender_balance - before_sender_balance)

    def test_withdraw_fee_with_penalty(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        self._engine.deposit_fee(
            context, tx_hash, self._sender, self._score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._engine.withdraw_fee(context, self._sender, tx_hash, block_number + period - 1)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_info = self._engine.get_score_fee_info(context, self._score_address, block_number)
        self.assertEqual(0, len(score_info.deposits))
        self.assertGreater(after_sender_balance - before_sender_balance, 0)
        self.assertLessEqual(after_sender_balance - before_sender_balance, amount)

    def test_get_deposit_info(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        before_sender_balance = self._icx_engine.get_balance(None, self._sender)
        self._engine.deposit_fee(
            context, tx_hash, self._sender, self._score_address, amount, block_number, period)
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self.assertEqual(amount, before_sender_balance - after_sender_balance)

        deposit = self._engine.get_deposit_info_by_id(context, tx_hash)

        self.assertEqual(tx_hash, deposit.id)
        self.assertEqual(self._score_address, deposit.score_address)
        self.assertEqual(self._sender, deposit.sender)
        self.assertEqual(amount, deposit.deposit_amount)
        self.assertEqual(block_number, deposit.created)
        self.assertEqual(block_number + period, deposit.expires)

    def test_get_available_step_with_sharing(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        step_price = 10 ** 10
        sender_step_limit = 10000
        block_number = randrange(100, 10000)
        max_step_limit = 1_000_000

        ratio = 50
        self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        available_steps = self._engine.get_total_available_step(context, self._sender,
                                                                self._score_address,
                                                                sender_step_limit, step_price,
                                                                block_number, max_step_limit)

        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(
            total_step - sender_step_limit, available_steps.get(self._score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

        ratio = 30
        self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        available_steps = self._engine.get_total_available_step(context, self._sender,
                                                                self._score_address,
                                                                sender_step_limit, step_price,
                                                                block_number, max_step_limit)

        total_step = sender_step_limit * 100 // (100 - ratio)
        self.assertEqual(
            total_step - sender_step_limit, available_steps.get(self._score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

    def test_get_available_step_without_sharing(self):
        context = IconScoreContext(IconScoreContextType.QUERY)

        step_price = 10 ** 10
        score_address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        block_number = randrange(100, 10000)
        sender_step_limit = 10000
        max_step_limit = 1_000_000

        available_steps = self._engine.get_total_available_step(context, self._sender,
                                                                score_address, sender_step_limit,
                                                                step_price, block_number,
                                                                max_step_limit)

        self.assertEqual(0, available_steps.get(score_address, 0))
        self.assertEqual(sender_step_limit, available_steps.get(self._sender, 0))

    def test_charge_transaction_fee_without_sharing(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)

        self._engine.deposit_fee(
            context, tx_hash, self._sender, self._score_address, amount, block_number, period)

        before_sender_balance = self._icx_engine.get_balance(context, self._sender)

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, block_number)

        after_sender_balance = self._icx_engine.get_balance(context, self._sender)

        self.assertEqual(step_price * used_step, before_sender_balance - after_sender_balance)

    def test_charge_transaction_fee_sharing_deposit(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        step_price = 10 ** 10
        used_step = 10 ** 10

        tx_hash = os.urandom(32)
        amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
        block_number = randrange(100, 10000)
        period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)
        self._engine.deposit_fee(
            context, tx_hash, self._sender, self._score_address, amount, block_number, period)

        ratio = 50
        self._engine.set_fee_sharing_ratio(context, self._sender, self._score_address, ratio)

        score_info = self._engine.get_score_fee_info(context, self._score_address, block_number)
        before_deposit_balance = score_info.available_deposit
        before_sender_balance = self._icx_engine.get_balance(None, self._sender)

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, block_number)

        score_info = self._engine.get_score_fee_info(context, self._score_address, block_number)
        after_deposit_balance = score_info.available_deposit
        after_sender_balance = self._icx_engine.get_balance(None, self._sender)

        score_charging_step = used_step * ratio // 100
        sender_charging_step = used_step - score_charging_step
        self.assertEqual(
            step_price * score_charging_step, before_deposit_balance - after_deposit_balance)
        self.assertEqual(
            step_price * sender_charging_step, before_sender_balance - after_sender_balance)

    # TODO test_charge_transaction_fee_sharing_virtual_step
    # TODO test_charge_transaction_fee_sharing_deposit_virtual_step
