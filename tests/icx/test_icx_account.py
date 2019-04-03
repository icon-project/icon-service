#!/usr/bin/env python3
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


import unittest

from iconservice import Address
from iconservice.base.exception import InvalidParamsException, OutOfBalanceException
from iconservice.icx.icx_account import Account, PartFlag
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.stake_part import StakePart
from iconservice.icx.delegation_part import DelegationPart

from tests import create_address


class TestAccount(unittest.TestCase):
    def test_account_flag(self):
        address: 'Address' = create_address()

        account: 'Account' = Account(address, 0)
        self.assertEqual(PartFlag.NONE, account.flag)

        coin_part: 'CoinPart' = CoinPart()
        account.init_coin_part_in_icx_storage(coin_part)
        self.assertEqual(PartFlag.COIN, account.flag)
        account.init_coin_part_in_icx_storage(None)
        self.assertEqual(PartFlag.NONE, account.flag)

        stake_part: 'StakePart' = StakePart()
        account.init_stake_part_in_icx_storage(stake_part)
        self.assertEqual(PartFlag.STAKE, account.flag)
        account.init_stake_part_in_icx_storage(None)
        self.assertEqual(PartFlag.NONE, account.flag)

        delegation_part: 'DelegationPart' = DelegationPart()
        account.init_delegation_part_in_icx_storage(delegation_part)
        self.assertEqual(PartFlag.DELEGATION, account.flag)
        account.init_delegation_part_in_icx_storage(None)
        self.assertEqual(PartFlag.NONE, account.flag)

        account.init_coin_part_in_icx_storage(coin_part)
        account.init_stake_part_in_icx_storage(stake_part)
        account.init_delegation_part_in_icx_storage(delegation_part)
        self.assertTrue(account.is_flag_on(PartFlag.COIN))
        self.assertTrue(account.is_flag_on(PartFlag.STAKE))
        self.assertTrue(account.is_flag_on(PartFlag.DELEGATION))
        self.assertEqual(PartFlag.COIN | PartFlag.STAKE | PartFlag.DELEGATION, account.flag)

        account.init_coin_part_in_icx_storage(None)
        account.init_stake_part_in_icx_storage(None)
        account.init_delegation_part_in_icx_storage(None)
        self.assertTrue(account.is_flag_on(PartFlag.NONE))
        self.assertEqual(PartFlag.NONE, account.flag)

    def test_coin_part(self):
        address: 'Address' = create_address()

        coin_part: 'CoinPart' = CoinPart()
        account: 'Account' = Account(address, 0)
        account.init_coin_part_in_icx_storage(coin_part)

        self.assertEqual(address, account.address)
        self.assertEqual(0, account.balance)

        account.deposit(100)
        self.assertEqual(100, account.balance)

        account.withdraw(100)
        self.assertEqual(0, account.balance)

        # wrong value
        self.assertRaises(InvalidParamsException, account.deposit, -10)

        # 0 transfer is possible
        old = account.balance
        account.deposit(0)
        self.assertEqual(old, account.balance)

        self.assertRaises(InvalidParamsException, account.withdraw, -11234)
        self.assertRaises(OutOfBalanceException, account.withdraw, 1)

        old = account.balance
        account.withdraw(0)
        self.assertEqual(old, account.balance)

    def test_account_for_stake(self):
        address: 'Address' = create_address()

        account = Account(address, 0)
        coin_part: 'CoinPart' = CoinPart()
        stake_part: 'StakePart' = StakePart()
        account.init_coin_part_in_icx_storage(coin_part)
        account.init_stake_part_in_icx_storage(stake_part)
        account.update()

        balance = 1000
        account.deposit(balance)

        stake1 = 500
        unstake_block_height = 0
        remain_balance = balance - stake1

        account.set_stake(stake1, 0)

        self.assertEqual(stake1, account.stake)
        self.assertEqual(0, account.unstake)
        self.assertEqual(unstake_block_height, account.unstake_block_height)
        self.assertEqual(remain_balance, account.balance)

        stake2 = 100
        block_height = 10
        unstake = stake1 - stake2
        remain_balance = balance - stake1
        account.set_stake(stake2, block_height)

        self.assertEqual(stake2, account.stake)
        self.assertEqual(unstake, account.unstake)
        self.assertEqual(block_height, account.unstake_block_height)
        self.assertEqual(remain_balance, account.balance)

        remain_balance = remain_balance + unstake
        account._current_block_height += 11
        self.assertEqual(remain_balance, account.balance)

    def test_account_for_delegation(self):
        target_accounts = []

        src_account = Account(create_address(), 0)
        src_delegation_part: 'DelegationPart' = DelegationPart()
        src_account.init_delegation_part_in_icx_storage(src_delegation_part)
        preps: list = []

        for _ in range(0, 10):
            address: 'Address' = create_address()
            target_account: 'Account' = Account(address, 0)
            target_delegation_part: 'DelegationPart' = DelegationPart()
            target_account.init_delegation_part_in_icx_storage(target_delegation_part)

            target_accounts.append(target_account)
            target_account.update_delegated_amount(10)
            preps.append((address, 10))
        src_account.set_delegations(preps)

        self.assertEqual(10, len(src_account.delegation_part.delegations))

        for i in range(0, 10):
            self.assertEqual(10, target_accounts[i].delegation_part.delegated_amount)


if __name__ == '__main__':
    unittest.main()
