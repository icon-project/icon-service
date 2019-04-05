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

from iconservice.base.address import ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.icx.base_part import BasePartState
from iconservice.icx.stake_part import StakePart
from tests import create_address


class TestStakePart(unittest.TestCase):

    def test_stake_part_from_bytes_to_bytes(self):
        part1 = StakePart()
        part1.normalize(0)
        data = part1.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(5, len(data))

        part2 = StakePart.from_bytes(data)
        part2.normalize(0)
        self.assertEqual(part1.stake, part2.stake)
        self.assertEqual(part1.unstake, part2.unstake)
        self.assertEqual(part1.unstake_block_height, part2.unstake_block_height)

        part3 = StakePart(10, 20, 30)
        part3.normalize(0)
        part4 = StakePart.from_bytes(part3.to_bytes())
        part4.normalize(0)
        self.assertEqual(part3.stake, part4.stake)
        self.assertEqual(part3.unstake, part4.unstake)
        self.assertEqual(part3.unstake_block_height, part4.unstake_block_height)

    def test_stake_part_update(self):
        stake: int = 10
        unstake: int = 0
        unstake_block_height: int = 0
        part1 = StakePart(stake, unstake, unstake_block_height)
        part1.normalize(0)
        self.assertEqual(stake, part1.stake)
        self.assertEqual(unstake, part1.unstake)
        self.assertEqual(unstake_block_height, part1.unstake_block_height)

        stake: int = 5
        unstake: int = 5
        unstake_block_height: int = 3
        part2 = StakePart(stake, unstake, unstake_block_height)
        part2.normalize(unstake_block_height + 1)
        self.assertEqual(stake, part2.stake)
        self.assertEqual(0, part2.unstake)
        self.assertEqual(0, part2.unstake_block_height)

    def test_stake_part(self):
        stake = 500
        unstake = 0
        unstake_block_height = 0

        stake_part: 'StakePart' = StakePart()
        stake_part.normalize(0)
        stake_part.add_stake(stake)

        self.assertEqual(stake, stake_part.stake)
        self.assertEqual(unstake, stake_part.unstake)
        self.assertEqual(unstake_block_height, stake_part.unstake_block_height)

        unstake = 100
        block_height = 10
        remain_stake = stake - unstake
        stake_part.set_unstake(block_height, unstake)

        self.assertEqual(remain_stake, stake_part.stake)
        self.assertEqual(unstake, stake_part.unstake)
        self.assertEqual(block_height, stake_part.unstake_block_height)

    def test_stake_part_make_key(self):
        key = StakePart.make_key(create_address())
        self.assertEqual(ICON_EOA_ADDRESS_BYTES_SIZE + len(StakePart.PREFIX) + 1, len(key))

        key = StakePart.make_key(create_address(1))
        self.assertEqual(ICON_CONTRACT_ADDRESS_BYTES_SIZE + len(StakePart.PREFIX), len(key))

    def test_stake_part_stake(self):
        part = StakePart()
        part.set_complete(True)
        self.assertEqual(0, part.stake)

    def test_stake_part_stake_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.stake)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_voting_weight(self):
        stake = 10
        part = StakePart(stake=stake)
        part.set_complete(True)
        self.assertEqual(stake, part.voting_weight)

    def test_stake_part_voting_weight_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.voting_weight)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_unstake(self):
        unstake = 10
        part = StakePart(unstake=unstake)
        part.set_complete(True)
        self.assertEqual(unstake, part.unstake)

    def test_stake_part_unstake_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.unstake)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_unstake_block_height(self):
        unstake_block_height = 10
        part = StakePart(unstake_block_height=unstake_block_height)
        part.set_complete(True)
        self.assertEqual(unstake_block_height, part.unstake_block_height)

    def test_stake_part_unstake_block_height_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.unstake_block_height)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_total_stake(self):
        stake = 10
        unstake = 20
        part = StakePart(stake=stake, unstake=unstake)
        part.set_complete(True)
        self.assertEqual(stake+unstake, part.total_stake)

    def test_stake_part_total_stake_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.total_stake)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_add_stake(self):
        part = StakePart()
        part.set_complete(True)

        stake = 100
        part.add_stake(100)
        self.assertEqual(stake, part.stake)
        self.assertTrue(part.is_set(BasePartState.DIRTY | BasePartState.COMPLETE))

    def test_stake_part_set_unstake_update(self):
        part = StakePart()
        part.set_complete(True)

        stake = 100
        block_height = 10
        part.add_stake(100)
        unstake = stake
        part.set_unstake(block_height, unstake)

        self.assertEqual(0, part.stake)
        self.assertEqual(stake, part.unstake)
        self.assertEqual(block_height, part.unstake_block_height)
        self.assertTrue(part.is_set(BasePartState.DIRTY | BasePartState.COMPLETE))

        block_height += block_height
        unstake = 10
        part.set_unstake(block_height, unstake)
        self.assertEqual(stake - unstake, part.stake)
        self.assertEqual(unstake, part.unstake)
        self.assertEqual(block_height, part.unstake_block_height)
        self.assertTrue(part.is_set(BasePartState.DIRTY | BasePartState.COMPLETE))

        refund_unstake = part.normalize(block_height + 1)
        self.assertEqual(unstake, refund_unstake)

    def test_delegation_part_equal(self):
        part1 = StakePart()
        part1.normalize(0)
        part2 = StakePart()
        part2.normalize(1)
        self.assertEqual(part1, part2)

        offset = 100
        part1.add_stake(offset)

        part3 = StakePart(stake=offset)
        part3.normalize(100)
        self.assertEqual(part1, part3)


if __name__ == '__main__':
    unittest.main()
