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
from unittest.mock import Mock

from iconservice import Address
from iconservice.base.exception import InvalidParamsException, OutOfBalanceException
from iconservice.icx.icx_account import Account
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.stake_part import StakePart
from iconservice.icx.delegation_part import DelegationPart

from tests import create_address


class TestAccount(unittest.TestCase):
    def test_account_flag(self):
        address: 'Address' = create_address()

        account: 'Account' = Account(address, 0)
        self.assertIsNone(account.coin_part)
        self.assertIsNone(account.stake_part)
        self.assertIsNone(account.delegation_part)

        coin_part: 'CoinPart' = CoinPart()
        account: 'Account' = Account(address, 0, coin_part=coin_part)
        self.assertIsNotNone(account.coin_part)
        self.assertIsNone(account.stake_part)
        self.assertIsNone(account.delegation_part)

        stake_part: 'StakePart' = StakePart()
        account: 'Account' = Account(address, 0, stake_part=stake_part)
        self.assertIsNone(account.coin_part)
        self.assertIsNotNone(account.stake_part)
        self.assertIsNone(account.delegation_part)

        delegation_part: 'DelegationPart' = DelegationPart()
        account: 'Account' = Account(address, 0, delegation_part=delegation_part)
        self.assertIsNone(account.coin_part)
        self.assertIsNone(account.stake_part)
        self.assertIsNotNone(account.delegation_part)

        account: 'Account' = Account(address, 0,
                                     coin_part=coin_part,
                                     stake_part=stake_part,
                                     delegation_part=delegation_part)
        self.assertIsNotNone(account.coin_part)
        self.assertIsNotNone(account.stake_part)
        self.assertIsNotNone(account.delegation_part)

    def test_coin_part(self):
        address: 'Address' = create_address()

        coin_part: 'CoinPart' = CoinPart()
        account: 'Account' = Account(address, 0, coin_part=coin_part)
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

        coin_part: 'CoinPart' = CoinPart()
        stake_part: 'StakePart' = StakePart()
        account = Account(address, 0, coin_part=coin_part, stake_part=stake_part)

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
        account.normalize()
        self.assertEqual(remain_balance, account.balance)

    def test_account_for_delegation(self):
        target_accounts = []

        src_delegation_part: 'DelegationPart' = DelegationPart()
        src_account = Account(create_address(), 0, delegation_part=src_delegation_part)
        preps: list = []

        for _ in range(0, 10):
            address: 'Address' = create_address()
            target_delegation_part: 'DelegationPart' = DelegationPart()
            target_account: 'Account' = \
                Account(address, 0, delegation_part=target_delegation_part)

            target_accounts.append(target_account)
            target_account.update_delegated_amount(10)
            preps.append((address, 10))

        src_account.set_delegations(preps)
        self.assertEqual(10, len(src_account.delegation_part.delegations))

        for i in range(10):
            self.assertEqual(10, target_accounts[i].delegation_part.delegated_amount)

    def test_account_balance(self):
        account = Account(create_address(), 0)
        self.assertEqual(0, account.balance)

        balance = 100
        coin_part = Mock(spec=CoinPart, balance=balance)
        account = Account(create_address(), 0, coin_part=coin_part)
        self.assertEqual(balance, account.balance)

    def test_account_stake(self):
        account = Account(create_address(), 0)
        self.assertEqual(0, account.stake)

        stake_part = StakePart(stake=100)
        account = Account(create_address(), 0, stake_part=stake_part)
        self.assertEqual(100, account.stake)

    def test_account_unstake(self):
        account = Account(create_address(), 0)
        self.assertEqual(0, account.unstake)

        stake_part = StakePart(unstake=200)
        account = Account(create_address(), 0, stake_part=stake_part)
        self.assertEqual(200, account.unstake)

    def test_account_unstake_block_height(self):
        account = Account(create_address(), 0)
        self.assertEqual(0, account.unstake_block_height)

        stake_part = StakePart(unstake_block_height=300)
        account = Account(create_address(), 0, stake_part=stake_part)
        self.assertEqual(300, account.unstake_block_height)

    def test_account_delegated_amount(self):
        account = Account(create_address(), 0)
        self.assertEqual(0, account.delegated_amount)

        delegation_part = DelegationPart(delegated_amount=100)
        account = Account(create_address(), 0, delegation_part=delegation_part)
        self.assertEqual(100, account.delegated_amount)

    def test_account_delegations(self):
        account = Account(create_address(), 0)
        self.assertEqual(None, account.delegations)

        delegations = [
            (create_address(), 100),
            (create_address(), 200),
            (create_address(), 300)
        ]
        delegation_part = DelegationPart(delegations=delegations)
        account = Account(create_address(), 0, delegation_part=delegation_part)
        self.assertEqual(delegations, account.delegations)
        self.assertEqual(600, account.delegations_amount)


if __name__ == '__main__':
    unittest.main()
