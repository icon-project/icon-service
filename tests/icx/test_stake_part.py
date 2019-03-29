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
from iconservice.icx.stake_part import StakePart
from tests import create_address


class TestStakePart(unittest.TestCase):

    def test_stake_part_from_bytes_to_bytes(self):
        address: 'Address' = create_address()

        account = StakePart(address)
        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(5, len(data))

        account2 = StakePart.from_bytes(data, address)
        self.assertEqual(account.stake, account2.stake)
        self.assertEqual(account.unstake, account2.unstake)
        self.assertEqual(account.unstake_block_height, account2.unstake_block_height)

        account._stake_amount = 10
        account._unstake_amount = 20
        account._unstake_block_height = 30

        account3 = StakePart.from_bytes(account.to_bytes(), address)
        self.assertEqual(account.stake, account3.stake)
        self.assertEqual(account.unstake, account3.unstake)
        self.assertEqual(account.unstake_block_height, account3.unstake_block_height)

    def test_stake_part(self):
        address: 'Address' = create_address()

        stake = 500
        unstake = 0
        unstake_block_height = 0

        stake_part: 'StakePart' = StakePart(address)
        stake_part.update_stake(stake)

        self.assertEqual(stake, stake_part.stake)
        self.assertEqual(unstake, stake_part.unstake)
        self.assertEqual(unstake_block_height, stake_part.unstake_block_height)

        unstake = 100
        block_height = 10
        remain_stake = stake - unstake
        stake_part.update_unstake(block_height, unstake)

        self.assertEqual(remain_stake, stake_part.stake)
        self.assertEqual(unstake, stake_part.unstake)
        self.assertEqual(block_height, stake_part.unstake_block_height)


if __name__ == '__main__':
    unittest.main()
