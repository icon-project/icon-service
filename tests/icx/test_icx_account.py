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
from iconservice.icon_constant import REVISION_4, REVISION_3
from iconservice.icx.icx_account import AccountType, Account, AccountOfStake, AccountOfDelegation, AccountDelegationInfo
from tests import create_address


class TestAccountType(unittest.TestCase):
    def test_account_type(self):
        self.assertTrue(AccountType.GENERAL == 0)
        self.assertTrue(AccountType.GENESIS == 1)
        self.assertTrue(AccountType.TREASURY == 2)

        self.assertTrue(str(AccountType.GENERAL) == 'GENERAL')
        self.assertTrue(str(AccountType.GENESIS) == 'GENESIS')
        self.assertTrue(str(AccountType.TREASURY) == 'TREASURY')

    def test_from_int(self):
        self.assertEqual(AccountType.GENERAL, AccountType.from_int(0))
        self.assertEqual(AccountType.GENESIS, AccountType.from_int(1))
        self.assertEqual(AccountType.TREASURY, AccountType.from_int(2))

        self.assertRaises(ValueError, AccountType.from_int, 3)


class TestAccount(unittest.TestCase):
    def test_account_revision_3(self):
        account1 = Account()
        self.assertIsNotNone(account1)
        self.assertIsNone(account1.address)
        self.assertTrue(account1.balance == 0)
        account1.address = create_address()

        account1.deposit(100)
        self.assertEqual(100, account1.balance)

        account1.withdraw(100)
        self.assertEqual(0, account1.balance)

        # wrong value
        self.assertRaises(InvalidParamsException, account1.deposit, -10)

        # 0 transfer is possible
        old = account1.balance
        account1.deposit(0)
        self.assertEqual(old, account1.balance)

        self.assertRaises(InvalidParamsException, account1.withdraw, -11234)
        self.assertRaises(OutOfBalanceException, account1.withdraw, 1)

        old = account1.balance
        account1.withdraw(0)
        self.assertEqual(old, account1.balance)

    def test_account_from_bytes_to_bytes_revision_3(self):
        account = Account()

        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        account2 = Account.from_bytes(data)
        self.assertFalse(account2.locked)
        self.assertEqual(AccountType.GENERAL, account2.type)
        self.assertEqual(0, account2.balance)

        account.type = AccountType.GENESIS
        account.deposit(1024)

        account3 = Account.from_bytes(account.to_bytes())
        self.assertEqual(AccountType.GENESIS, account3.type)
        self.assertEqual(1024, account3.balance)

    def test_account_from_bytes_to_bytes_revision_4(self):
        account = Account()

        data = account.to_bytes(REVISION_4)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(9, len(data))

        account2 = Account.from_bytes(data)
        self.assertFalse(account2.locked)
        self.assertEqual(AccountType.GENERAL, account2.type)
        self.assertEqual(0, account2.balance)

        account.type = AccountType.GENESIS
        account.deposit(1024)

        account3 = Account.from_bytes(account.to_bytes(REVISION_4))
        self.assertEqual(AccountType.GENESIS, account3.type)
        self.assertEqual(1024, account3.balance)

    def test_account_from_bytes_to_bytes_old_db_load_revision_4(self):
        account = Account()

        balance = 1024
        account.type = AccountType.GENERAL
        account.deposit(balance)

        account1 = Account.from_bytes(account.to_bytes(REVISION_3))
        self.assertEqual(account, account1)

        data: bytes = account.to_bytes(REVISION_4)
        account2 = Account.from_bytes(data)
        self.assertEqual(account, account2)


class TestAccountOfStake(unittest.TestCase):

    def test_account_of_stake_from_bytes_to_bytes(self):
        address: 'Address' = create_address()

        account = AccountOfStake(address)
        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(9, len(data))

        account2 = AccountOfStake.from_bytes(data, address)
        self.assertEqual(account.stake_amount, account2.stake_amount)
        self.assertEqual(account.unstake_amount, account2.unstake_amount)
        self.assertEqual(account.unstake_block_height, account2.unstake_block_height)

        account._stake_amount = 10
        account._unstake_amount = 20
        account._unstake_block_height = 30

        account3 = AccountOfStake.from_bytes(account.to_bytes(), address)
        self.assertEqual(account.stake_amount, account3.stake_amount)
        self.assertEqual(account.unstake_amount, account3.unstake_amount)
        self.assertEqual(account.unstake_block_height, account3.unstake_block_height)

    def test_account_for_stake(self):
        address: 'Address' = create_address()

        account = Account()
        account.address = address
        account.type = AccountType.GENERAL

        balance = 1000
        account.deposit(balance)

        stake = 500
        unstake = 0
        unstake_block_height = 0
        remain_balance = balance - stake

        account_of_stake = AccountOfStake(address)
        account_of_stake.stake(stake, account)

        self.assertEqual(stake, account_of_stake.stake_amount)
        self.assertEqual(unstake, account_of_stake.unstake_amount)
        self.assertEqual(unstake_block_height, account_of_stake.unstake_block_height)
        self.assertEqual(remain_balance, account.balance)

        unstake = 100
        block_height = 10
        remain_stake = stake - unstake
        remain_balance = balance - stake
        account_of_stake.unstake(block_height, unstake)

        self.assertEqual(remain_stake, account_of_stake.stake_amount)
        self.assertEqual(unstake, account_of_stake.unstake_amount)
        self.assertEqual(block_height, account_of_stake.unstake_block_height)
        self.assertEqual(remain_balance, account.balance)

        self.assertEqual(0, account_of_stake.extension_balance(block_height))
        self.assertEqual(unstake, account_of_stake.extension_balance(block_height + 1))


class TestAccountOfDelegation(unittest.TestCase):

    def test_account_of_delegation_from_bytes_to_bytes(self):
        address: 'Address' = create_address()

        account = AccountOfDelegation(address)
        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(6, len(data))

        account2 = AccountOfDelegation.from_bytes(data, address)
        self.assertEqual(account.delegated_amount, account2.delegated_amount)
        self.assertEqual(account.delegations, account2.delegations)

    def test_account_for_delegation(self):
        target_accounts = []

        src_account = AccountOfDelegation(create_address())

        for _ in range(0, 10):
            target_account = AccountOfDelegation(create_address())
            target_accounts.append(target_account)

            src_account.delegate(target_account, 10)

        self.assertEqual(10, len(src_account.delegations))

        for i in range(0, 10):
            self.assertEqual(10, target_accounts[i].delegated_amount)

        for i in range(0, 10):
            src_account.delegate(target_accounts[i], 0)
        self.assertEqual(0, len(src_account.delegations))


if __name__ == '__main__':
    unittest.main()
