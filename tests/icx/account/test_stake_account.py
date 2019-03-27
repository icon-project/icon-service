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
from iconservice.icx.account.stake_account import StakeAccount
from tests import create_address


class TestStakeAccount(unittest.TestCase):

    def test_stake_account_from_bytes_to_bytes(self):
        address: 'Address' = create_address()

        account = StakeAccount(address)
        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(9, len(data))

        account2 = StakeAccount.from_bytes(data, address)
        self.assertEqual(account.stake_amount, account2.stake_amount)
        self.assertEqual(account.unstake_amount, account2.unstake_amount)
        self.assertEqual(account.unstake_block_height, account2.unstake_block_height)

        account._stake_amount = 10
        account._unstake_amount = 20
        account._unstake_block_height = 30

        account3 = StakeAccount.from_bytes(account.to_bytes(), address)
        self.assertEqual(account.stake_amount, account3.stake_amount)
        self.assertEqual(account.unstake_amount, account3.unstake_amount)
        self.assertEqual(account.unstake_block_height, account3.unstake_block_height)

    def test_stake_account(self):
        address: 'Address' = create_address()

        stake = 500
        unstake = 0
        unstake_block_height = 0

        stake_account = StakeAccount(address)
        stake_account.stake(stake)

        self.assertEqual(stake, stake_account.stake_amount)
        self.assertEqual(unstake, stake_account.unstake_amount)
        self.assertEqual(unstake_block_height, stake_account.unstake_block_height)

        unstake = 100
        block_height = 10
        remain_stake = stake - unstake
        stake_account.unstake(block_height, unstake)

        self.assertEqual(remain_stake, stake_account.stake_amount)
        self.assertEqual(unstake, stake_account.unstake_amount)
        self.assertEqual(block_height, stake_account.unstake_block_height)


if __name__ == '__main__':
    unittest.main()
