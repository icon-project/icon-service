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
from iconservice.base.exception import InvalidRequestException, OutOfBalanceException
from iconservice.database.db import ContextDatabase
from iconservice.deploy import DeployState
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployInfo
from iconservice.fee.fee_engine import FeeEngine
from iconservice.fee.fee_storage import FeeStorage
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


def patch_fee_storage(fee_storage: FeeStorage):
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

    fee_storage.put_score_fee = put
    fee_storage.get_score_fee = get
    fee_storage.delete_score_fee = delete
    fee_storage.put_deposit = put
    fee_storage.get_deposit = get
    fee_storage.delete_deposit = delete


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
        self._icx_engine = IcxEngine()

        fee_storage = FeeStorage(context_db)
        patch_fee_storage(fee_storage)

        deploy_storage.put_deploy_info(context, deploy_info)
        self._icx_engine.open(icx_storage)

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, 100000000 * 10 ** 18)

        treasury = Account(
            AccountType.TREASURY, Address.from_data(AddressPrefix.EOA, os.urandom(20)))
        self._icx_engine._init_special_account(context, treasury)

        self._engine = FeeEngine(deploy_storage, fee_storage, icx_storage, self._icx_engine)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

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
        # noinspection PyUnresolvedReferences
        self.assertEqual('Invalid deposit amount', e.exception.message)

        # invalid amount (overflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_amount = \
                randrange(FeeEngine._MAX_DEPOSIT_AMOUNT + 1, FeeEngine._MAX_DEPOSIT_AMOUNT * 10)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     inv_amount, block_number, period)
        # noinspection PyUnresolvedReferences
        self.assertEqual('Invalid deposit amount', e.exception.message)

        # invalid period (underflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_period = randrange(0, FeeEngine._MIN_DEPOSIT_PERIOD - 1)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, inv_period)
        # noinspection PyUnresolvedReferences
        self.assertEqual('Invalid deposit period', e.exception.message)

        # invalid period (overflow)
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_period = \
                randrange(FeeEngine._MAX_DEPOSIT_PERIOD + 1, FeeEngine._MAX_DEPOSIT_PERIOD * 10)
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, inv_period)
        # noinspection PyUnresolvedReferences
        self.assertEqual('Invalid deposit period', e.exception.message)

        # invalid owner
        # noinspection PyTypeChecker
        with self.assertRaises(InvalidRequestException) as e:
            inv_sender = Address.from_data(AddressPrefix.EOA, os.urandom(20))
            self._engine.deposit_fee(context, tx_hash, inv_sender, self._score_address,
                                     amount, block_number, period)
        # noinspection PyUnresolvedReferences
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
        with self.assertRaises(OutOfBalanceException) as e:
            self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address,
                                     amount, block_number, period)
        # noinspection PyUnresolvedReferences
        self.assertEqual('Out of balance', e.exception.message)

    def test_deposit_fee_available_head_ids(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        tx_hash = os.urandom(32)
        amount = 10000 * 10 ** 18
        block_number = 1000

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, amount)

        fee_info = self._engine._get_or_create_score_fee(context, self._score_address)

        self.assertEqual(fee_info.available_head_id_of_virtual_step, None)
        self.assertEqual(fee_info.available_head_id_of_deposit, None)

        self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address, amount, block_number,
                                 FeeEngine._MIN_DEPOSIT_PERIOD)

        fee_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(fee_info.available_head_id_of_virtual_step, tx_hash)
        self.assertEqual(fee_info.available_head_id_of_deposit, tx_hash)

    def test_deposit_fee_expires_updated(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        tx_hash = os.urandom(32)
        amount = 10000 * 10 ** 18
        block_number = 1000
        period = FeeEngine._MIN_DEPOSIT_PERIOD

        self._icx_engine.init_account(
            context, AccountType.GENERAL, 'sender', self._sender, amount)

        fee_info = self._engine._get_or_create_score_fee(context, self._score_address)

        self.assertEqual(fee_info.expires_of_virtual_step, -1)
        self.assertEqual(fee_info.expires_of_deposit, -1)

        self._engine.deposit_fee(context, tx_hash, self._sender, self._score_address, amount, block_number, period)

        fee_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(fee_info.expires_of_virtual_step, block_number + period)
        self.assertEqual(fee_info.expires_of_deposit, block_number + period)

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

    def test_withdraw_fee_and_updates_previous_and_next_link(self):
        """
        Given: There are four deposits.
        When : Withdraws all of them sequentially.
        Then : Checks if the previous and next link update correctly.
        """
        context = IconScoreContext(IconScoreContextType.INVOKE)

        cnt_deposit = 4
        block_number = randrange(100, 10000)
        arr_tx_hash = []
        for i in range(cnt_deposit):
            arr_tx_hash.append(os.urandom(32))
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            period = randrange(FeeEngine._MIN_DEPOSIT_PERIOD, FeeEngine._MAX_DEPOSIT_PERIOD)
            block_number += 1
            self._engine.deposit_fee(
                context, arr_tx_hash[i], self._sender, self._score_address, amount, block_number, period)

        for i in range(cnt_deposit):
            target_deposit = self._engine.get_deposit_info_by_id(context, arr_tx_hash[i])
            self._engine.withdraw_fee(context, self._sender, arr_tx_hash[i], block_number + period // 2)

            if cnt_deposit - 1 == i:
                self.assertIsNone(target_deposit.next_id)
                break

            next_deposit = self._engine.get_deposit_info_by_id(context, target_deposit.next_id)
            self.assertEqual(next_deposit.prev_id, None)

    def test_withdraw_fee_when_available_head_id_of_virtual_step_is_same_as_deposit_id(self):
        """
        Given: There are four deposits. Only the last deposit has enough to long period.
        When : Available head id of the virtual step is same as deposit id.
        Then : Searches for next deposit id which is available to use virtual step
               and where expires of the deposit is more than current block height.
               In the test, only the last deposit is available.
        """
        context = IconScoreContext(IconScoreContextType.INVOKE)

        cnt_deposit = 4
        block_number = randrange(100, 10000)
        arr_tx_hash = []
        for i in range(cnt_deposit):
            arr_tx_hash.append(os.urandom(32))
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            block_number += 1

            if i != cnt_deposit - 1:
                period = FeeEngine._MIN_DEPOSIT_PERIOD
            else:
                period = FeeEngine._MAX_DEPOSIT_PERIOD

            self._engine.deposit_fee(
                context, arr_tx_hash[i], self._sender, self._score_address, amount, block_number, period)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_virtual_step, arr_tx_hash[0])

        self._engine.withdraw_fee(context, self._sender, arr_tx_hash[0],
                                  block_number + FeeEngine._MAX_DEPOSIT_PERIOD // 2)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_virtual_step, arr_tx_hash[len(arr_tx_hash) - 1])

    def test_withdraw_fee_when_available_head_id_of_deposit_is_same_as_deposit_id(self):
        """
        Given: There are four deposits. Only the third deposit has enough long period.
        When : Available head id of deposit is same as deposit id.
        Then : Searches for next deposit id which is available to use deposit
               and where expires of the deposit is more than current block height.
               In the test, only the third deposit is available.
        """
        context = IconScoreContext(IconScoreContextType.INVOKE)

        cnt_deposit = 4
        block_number = randrange(100, 10000)
        arr_tx_hash = []
        for i in range(cnt_deposit):
            arr_tx_hash.append(os.urandom(32))
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            block_number += 1

            if i != cnt_deposit - 2:
                period = FeeEngine._MIN_DEPOSIT_PERIOD
            else:
                period = FeeEngine._MAX_DEPOSIT_PERIOD

            self._engine.deposit_fee(
                context, arr_tx_hash[i], self._sender, self._score_address, amount, block_number, period)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_deposit, arr_tx_hash[0])

        self._engine.withdraw_fee(context, self._sender, arr_tx_hash[0],
                                  block_number + FeeEngine._MAX_DEPOSIT_PERIOD // 2)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_deposit, arr_tx_hash[len(arr_tx_hash) - 2])

    def test_withdraw_fee_to_check_setting_on_next_max_expires(self):
        """
        Given: There are four deposits.
        When : Expires of the withdrawal deposit is same as expires.
        Then : Searches for max expires which is more than current block height.
        """
        context = IconScoreContext(IconScoreContextType.INVOKE)

        cnt_deposit = 4
        block_number = randrange(100, 10000)
        arr_tx_hash = []
        last_expires = 0
        org_last_expires = 0
        for i in range(cnt_deposit):
            arr_tx_hash.append(os.urandom(32))
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            block_number += 1

            if i != 0:
                period = FeeEngine._MIN_DEPOSIT_PERIOD
                if block_number + period > last_expires:
                    last_expires = block_number + period
            else:
                period = FeeEngine._MAX_DEPOSIT_PERIOD
                org_last_expires = block_number + period
            self._engine.deposit_fee(
                context, arr_tx_hash[i], self._sender, self._score_address, amount, block_number, period)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_virtual_step, arr_tx_hash[0])
        self.assertEqual(score_info.expires_of_virtual_step, org_last_expires)
        self.assertEqual(score_info.expires_of_deposit, org_last_expires)

        self._engine.withdraw_fee(context, self._sender, arr_tx_hash[0],
                                  block_number + FeeEngine._MIN_DEPOSIT_PERIOD // 2)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.expires_of_virtual_step, last_expires)
        self.assertEqual(score_info.expires_of_deposit, last_expires)

    def test_withdraw_fee_of_last_deposit_to_check_setting_on_next_max_expires(self):
        """
        Given: There are four deposits.
        When : Expires of the withdrawal deposit which is the last one is same as expires.
        Then : Searches for max expires which is more than current block height.
        """
        context = IconScoreContext(IconScoreContextType.INVOKE)

        cnt_deposit = 4
        block_number = randrange(100, 10000)
        arr_tx_hash = []
        last_expires = 0
        org_last_expires = 0
        for i in range(cnt_deposit):
            arr_tx_hash.append(os.urandom(32))
            amount = randrange(FeeEngine._MIN_DEPOSIT_AMOUNT, FeeEngine._MAX_DEPOSIT_AMOUNT)
            block_number += 1

            if i != cnt_deposit-1:
                period = FeeEngine._MIN_DEPOSIT_PERIOD
                if block_number + period > last_expires:
                    last_expires = block_number + period
            else:
                period = FeeEngine._MAX_DEPOSIT_PERIOD
                org_last_expires = block_number + period
            self._engine.deposit_fee(
                context, arr_tx_hash[i], self._sender, self._score_address, amount, block_number, period)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.available_head_id_of_virtual_step, arr_tx_hash[0])
        self.assertEqual(score_info.available_head_id_of_deposit, arr_tx_hash[0])
        self.assertEqual(score_info.expires_of_virtual_step, org_last_expires)
        self.assertEqual(score_info.expires_of_deposit, org_last_expires)

        # Withdraws the last one
        self._engine.withdraw_fee(context, self._sender, arr_tx_hash[cnt_deposit-1],
                                  block_number + FeeEngine._MIN_DEPOSIT_PERIOD // 2)

        score_info = self._engine._get_or_create_score_fee(context, self._score_address)
        self.assertEqual(score_info.expires_of_virtual_step, last_expires)
        self.assertEqual(score_info.expires_of_deposit, last_expires)

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
        context.fee_sharing_ratio = ratio

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

    def test_charge_fee_from_score_by_virtual_step_single_deposit(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
        When :  Current  block is 120 so  1st deposit is unavailable
        Then :  Pays fee by virtual step of 2nd.
                update indices to 2nd
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 100),
            (os.urandom(32), 50, 180, 100, 100),
            (os.urandom(32), 70, 150, 100, 100),
            (os.urandom(32), 90, 250, 100, 100),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 80

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        before_virtual_step = score_info.available_virtual_step

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(used_step, before_virtual_step - after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(deposits[1][0], score_fee_info.available_head_id_of_virtual_step)

    def test_charge_fee_from_score_by_virtual_step_single_deposit_next_head(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
        When :  Current  block is 120 so  1st deposit is unavailable
        Then :  Pays fee by virtual step of 2nd.
                the virtual steps in 2nd are fully consumed
                update indices to 3rd
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 100),
            (os.urandom(32), 50, 180, 100, 100),
            (os.urandom(32), 70, 150, 100, 100),
            (os.urandom(32), 90, 250, 100, 100),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 100

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        before_virtual_step = score_info.available_virtual_step

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(used_step, before_virtual_step - after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(deposits[2][0], score_fee_info.available_head_id_of_virtual_step)

    def test_charge_fee_from_score_by_virtual_step__single_deposit_next_head_next_expire(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
        When :  Current  block is 190 so  4th, 5th deposits are available
        Then :  Pays fee by virtual step of 4th.
                the virtual steps in 4th are fully consumed
                update indices to 5th
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 100),
            (os.urandom(32), 50, 180, 100, 100),
            (os.urandom(32), 70, 150, 100, 100),
            (os.urandom(32), 90, 250, 100, 100),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 190
        used_step = 100

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        before_virtual_step = score_info.available_virtual_step

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(used_step, before_virtual_step - after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(deposits[4][0], score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(deposits[4][2], score_fee_info.expires_of_virtual_step)

    def test_charge_fee_from_score_by_virtual_step__single_deposit_next_head_next_expire_none(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
        When :  Current  block is 210 so only 4th deposit is available
        Then :  Pays fee by virtual step of 4th.
                the virtual steps in 4th are fully consumed
                should update indices but there are no more available deposits
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 100),
            (os.urandom(32), 50, 180, 100, 100),
            (os.urandom(32), 70, 150, 100, 100),
            (os.urandom(32), 90, 250, 100, 100),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 210
        used_step = 100

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        before_virtual_step = score_info.available_virtual_step

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(used_step, before_virtual_step - after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

    def test_charge_fee_from_score_by_virtual_step_multiple_deposit(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
        When :  Current  block is 120 so 1st deposit is unavailable
        Then :  Pays fee by virtual step through 2nd, 3rd, 4th.
                the virtual steps in 2nd, 3rd are fully consumed
                update indices to 4th
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 100),
            (os.urandom(32), 50, 180, 100, 100),
            (os.urandom(32), 70, 150, 100, 100),
            (os.urandom(32), 90, 250, 100, 100),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 250

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        before_virtual_step = score_info.available_virtual_step

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(used_step, before_virtual_step - after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(deposits[3][0], score_fee_info.available_head_id_of_virtual_step)

    def test_charge_fee_from_score_by_combine_by_single_deposit(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 5th deposit
        When :  Current  block is 120 so 1st deposit is unavailable
                Remaining virtual steps are not enough to pay fees
        Then :  Pays fee by virtual step first.
                Pays remaining fee by deposit of 2nd
                update indices to 2nd
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 0),
            (os.urandom(32), 110, 200, 100, 50)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 70

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        self.assertEqual(deposits[1][0], score_fee_info.available_head_id_of_deposit)

    def test_charge_fee_from_score_by_combine_next_head(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 5th deposit
        When :  Current  block is 120 so 1st deposit is unavailable
                Remaining virtual steps are not enough to pay fees
        Then :  Pays fee by virtual step first.
                Pays remaining fee by deposit of 2nd
                2nd deposit is fully consumed so update indices to 3rd
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 0),
            (os.urandom(32), 110, 200, 100, 50)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 140

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        self.assertEqual(deposits[2][0], score_fee_info.available_head_id_of_deposit)

    def test_charge_fee_from_score_by_combine_next_head_next_expire(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 5th deposit
        When :  Current  block is 190 so 1st, 2nd, 3rd deposits are unavailable
                Remaining virtual steps are not enough to pay fees
        Then :  Pays fee by virtual step first.
                Pays remaining fee by deposit of 4th
                4th deposit is fully consumed so update indices to 5th
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 0),
            (os.urandom(32), 110, 200, 100, 50)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 190
        used_step = 140

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        self.assertEqual(deposits[4][0], score_fee_info.available_head_id_of_deposit)
        self.assertEqual(deposits[4][2], score_fee_info.expires_of_deposit)

    def test_charge_fee_from_score_by_combine_next_head_next_expire_none(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 4th and 5th deposit
        When :  Current  block is 220 so 5th deposit is unavailable
                Remaining virtual steps are not enough to pay fees
        Then :  Pays fee by virtual step first.
                Pays remaining fee by deposit of 4th
                All available deposits are consumed so make the SCORE disabled
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 50),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 220
        used_step = 140

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        self.assertEqual(None, score_fee_info.available_head_id_of_deposit)
        self.assertEqual(-1, score_fee_info.expires_of_deposit)

    def test_charge_fee_from_score_by_combine_multiple_deposit(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 5th deposit
        When :  Current  block is 120 so 1st deposit is unavailable
                Remaining virtual steps are not enough to pay fees
        Then :  Pays fee by virtual step first.
                Pays remaining fee by deposit through 2nd and 3rd deposit.
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 0),
            (os.urandom(32), 110, 200, 100, 50)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 120
        used_step = 230

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        # Asserts indices are updated
        self.assertEqual(deposits[3][0], score_fee_info.available_head_id_of_deposit)
        self.assertEqual(deposits[3][2], score_fee_info.expires_of_deposit)

    def test_charge_fee_from_score_by_combine_additional_pay(self):
        """
        Given:  Five deposits. The fourth deposit is the max expire.
                Remaining virtual steps are in 4th and 5th deposit
        When :  Current  block is 220 so 5th deposit is unavailable
                Remaining virtual steps are not enough to pay fees
                Available deposits are also not enough to pay fees
        Then :  Pays fees regardless minimum remaining amount
                and make the SCORE disabled
        """

        context = IconScoreContext(IconScoreContextType.INVOKE)

        # tx_hash, from_block, to_block, deposit_amount, virtual_step_amount
        deposits = [
            (os.urandom(32), 10, 100, 100, 0),
            (os.urandom(32), 50, 180, 100, 0),
            (os.urandom(32), 70, 150, 100, 0),
            (os.urandom(32), 90, 250, 100, 50),
            (os.urandom(32), 110, 200, 100, 100)
        ]
        self._set_up_deposits(context, deposits)

        step_price = 1
        current_block = 220
        used_step = 150

        self._engine.charge_transaction_fee(
            context, self._sender, self._score_address, step_price, used_step, current_block)

        score_info = self._engine.get_score_fee_info(context, self._score_address, current_block)
        after_virtual_step = score_info.available_virtual_step

        self.assertEqual(0, after_virtual_step)

        score_fee_info = self._engine._fee_storage.get_score_fee(context, self._score_address)
        # Asserts virtual step disabled
        self.assertEqual(None, score_fee_info.available_head_id_of_virtual_step)
        self.assertEqual(-1, score_fee_info.expires_of_virtual_step)

        # Asserts deposit disabled
        self.assertEqual(None, score_fee_info.available_head_id_of_deposit)
        self.assertEqual(-1, score_fee_info.expires_of_deposit)

    def _set_up_deposits(self, context, deposits):
        context.fee_sharing_ratio = 100

        FeeEngine._MIN_DEPOSIT_PERIOD = 50
        FeeEngine._MIN_DEPOSIT_AMOUNT = 10
        FeeEngine._MIN_REMAINING_AMOUNT = 10

        for deposit in deposits:
            tx_hash = deposit[0]
            amount = deposit[3]
            block_number = deposit[1]
            period = deposit[2] - block_number

            self._engine._calculate_virtual_step_issuance = Mock(return_value=deposit[4])

            self._engine.deposit_fee(
                context, tx_hash, self._sender, self._score_address, amount, block_number, period)
