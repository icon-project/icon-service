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
from iconservice.icx.icx_account import AccountFlag, Account
from iconservice.icx.account.coin_account import CoinAccount
from iconservice.icx.account.stake_account import StakeAccount
from iconservice.icx.account.delegation_account import DelegationAccount

from tests import create_address


class TestAccount(unittest.TestCase):
    def test_account_flag(self):
        address: 'Address' = create_address()

        account: 'Account' = Account(address)
        self.assertEqual(AccountFlag.NONE, account.flag)

        coin_account: 'CoinAccount' = CoinAccount(address)
        account.coin_account = coin_account
        self.assertEqual(AccountFlag.COIN, account.flag)
        account.coin_account = None
        self.assertEqual(AccountFlag.NONE, account.flag)

        stake_account: 'StakeAccount' = StakeAccount(address)
        account.stake_account = stake_account
        self.assertEqual(AccountFlag.STAKE, account.flag)
        account.stake_account = None
        self.assertEqual(AccountFlag.NONE, account.flag)

        delegation_account: 'DelegationAccount' = DelegationAccount(address)
        account.delegation_account = delegation_account
        self.assertEqual(AccountFlag.DELEGATION, account.flag)
        account.delegation_account = None
        self.assertEqual(AccountFlag.NONE, account.flag)

        account.coin_account = coin_account
        account.stake_account = stake_account
        account.delegation_account = delegation_account
        self.assertTrue(account.is_flag_on(AccountFlag.COIN))
        self.assertTrue(account.is_flag_on(AccountFlag.STAKE))
        self.assertTrue(account.is_flag_on(AccountFlag.DELEGATION))
        self.assertEqual(AccountFlag.COIN|AccountFlag.STAKE|AccountFlag.DELEGATION, account.flag)

        account.coin_account = None
        account.stake_account = None
        account.delegation_account = None
        self.assertTrue(account.is_flag_on(AccountFlag.NONE))
        self.assertEqual(AccountFlag.NONE, account.flag)

    def test_coin_account(self):
        address: 'Address' = create_address()

        coin_account: 'CoinAccount' = CoinAccount(address)
        account: 'Account' = Account(address)
        account.coin_account = coin_account

        self.assertEqual(address, account.address)
        self.assertEqual(0, account.get_balance(0))

        account.deposit(100)
        self.assertEqual(100, account.get_balance(0))

        account.withdraw(100)
        self.assertEqual(0, account.get_balance(0))

        # wrong value
        self.assertRaises(InvalidParamsException, account.deposit, -10)

        # 0 transfer is possible
        old = account.get_balance(0)
        account.deposit(0)
        self.assertEqual(old, account.get_balance(0))

        self.assertRaises(InvalidParamsException, account.withdraw, -11234)
        self.assertRaises(OutOfBalanceException, account.withdraw, 1)

        old = account.get_balance(0)
        account.withdraw(0)
        self.assertEqual(old, account.get_balance(0))

    def test_account_for_stake(self):
        address: 'Address' = create_address()

        account = Account(address)
        coin_account: 'CoinAccount' = CoinAccount(address)
        stake_account: 'StakeAccount' = StakeAccount(address)
        account.coin_account: 'CoinAccount' = coin_account
        account.stake_account: 'StakeAccount' = stake_account

        balance = 1000
        account.deposit(balance)

        stake = 500
        unstake = 0
        unstake_block_height = 0
        remain_balance = balance - stake

        account.stake(stake)

        self.assertEqual(stake, account.get_stake_amount())
        self.assertEqual(unstake, account.get_unstake_amount())
        self.assertEqual(unstake_block_height, account.get_unstake_block_height())
        self.assertEqual(remain_balance, account.get_balance(0))

        unstake = 100
        block_height = 10
        remain_stake = stake - unstake
        remain_balance = balance - stake
        account.unstake(block_height, unstake)

        self.assertEqual(remain_stake, account.get_stake_amount())
        self.assertEqual(unstake, account.get_unstake_amount())
        self.assertEqual(block_height, account.get_unstake_block_height())
        self.assertEqual(remain_balance, account.get_balance(block_height))

        remain_balance = remain_balance + unstake
        self.assertEqual(remain_balance, account.get_balance(block_height + 1))

    def test_account_for_delegation(self):
        target_accounts = []

        src_account = Account(create_address())
        src_delegation_account: 'DelegationAccount' = DelegationAccount(src_account.address)
        src_account.delegation_account = src_delegation_account

        for _ in range(0, 10):
            target_account: 'Account' = Account(create_address())
            target_delegation_account: 'DelegationAccount' = DelegationAccount(target_account.address)
            target_account.delegation_account = target_delegation_account

            target_accounts.append(target_account)
            src_account.delegate(target_account, 10)

        self.assertEqual(10, len(src_account.delegation_account.delegations))

        for i in range(0, 10):
            self.assertEqual(10, target_accounts[i].delegation_account.delegated_amount)

        for i in range(0, 10):
            src_account.delegate(target_accounts[i], 0)
        src_account.trim_deletions()
        self.assertEqual(0, len(src_account.delegation_account.delegations))


if __name__ == '__main__':
    unittest.main()
