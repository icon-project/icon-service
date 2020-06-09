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
import copy
import random
import unittest

from iconservice.base.address import ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.icon_constant import Revision, UNSTAKE_SLOT_MAX
from iconservice.icx.base_part import BasePartState
from iconservice.icx.stake_part import StakePart
from tests import create_address


class TestStakePart(unittest.TestCase):

    def test_stake_part_from_bytes_to_bytes(self):
        part1 = StakePart()
        part1.normalize(0)
        data = part1.to_bytes(Revision.IISS.value)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(5, len(data))

        part2 = StakePart.from_bytes(data)
        part2.normalize(0)
        self.assertEqual(part1.stake, part2.stake)
        self.assertEqual(part1.unstake, part2.unstake)
        self.assertEqual(part1.unstake_block_height, part2.unstake_block_height)

        part3 = StakePart(10, 20, 30)
        part3.normalize(0)
        part4 = StakePart.from_bytes(part3.to_bytes(Revision.IISS.value))
        part4.normalize(0)
        self.assertEqual(part3.stake, part4.stake)
        self.assertEqual(part3.unstake, part4.unstake)
        self.assertEqual(part3.unstake_block_height, part4.unstake_block_height)

    def test_stake_part_from_bytes_to_bytes_multiple_unstake(self):
        part1 = StakePart()
        part1.normalize(0)
        data = part1.to_bytes(Revision.MULTIPLE_UNSTAKE.value)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(6, len(data))

        part2 = StakePart.from_bytes(data)
        part2.normalize(0)
        self.assertEqual(part1.stake, part2.stake)
        self.assertEqual(part1.unstake, part2.unstake)
        self.assertEqual(part1.unstake_block_height, part2.unstake_block_height)
        self.assertEqual(part1.unstakes_info, part2.unstakes_info)

        part3 = StakePart(10, 20, 30)
        part3.normalize(0)
        part4 = StakePart.from_bytes(part3.to_bytes(Revision.MULTIPLE_UNSTAKE.value))
        part4.normalize(0)
        self.assertEqual(part3.stake, part4.stake)
        self.assertEqual(part3.unstake, part4.unstake)
        self.assertEqual(part3.unstakes_info, part4.unstakes_info)

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

    def test_stake_part_update_multiple_unstake(self):
        stake: int = 5
        block_height = 3
        unstake_info1 = [10, 1]
        unstake_info2 = [20, 2]
        unstake_info3 = [40, 3]
        unstake_info4 = [30, 5]
        unstake_info5 = [100, 5]
        unstakes_info = [unstake_info1, unstake_info2, unstake_info3, unstake_info4, unstake_info5]
        part = StakePart(stake=stake, unstakes_info=unstakes_info)
        part.set_complete(True)
        part.normalize(block_height)
        self.assertEqual(stake, part.stake)
        self.assertEqual(0, part.unstake)
        self.assertEqual(0, part.unstake_block_height)
        expected_info = [[40, 3], [30, 5], [100, 5]]
        self.assertEqual(expected_info, part.unstakes_info)

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

    def test_set_unstakes_info(self):
        stake = 500
        unstake = 0
        unstake_block_height = 0

        stake_part: 'StakePart' = StakePart()
        stake_part.normalize(0)
        stake_part.add_stake(stake)

        self.assertEqual(stake, stake_part.stake)
        self.assertEqual(unstake, stake_part.unstake)
        self.assertEqual(unstake_block_height, stake_part.unstake_block_height)

        # test adding unstakes
        unstakes_info = [[random.randint(10, 100), index + 1] for index in range(UNSTAKE_SLOT_MAX)]

        for i in range(len(unstakes_info)):
            unstake = sum(map(lambda info: info[0], unstakes_info[:i+1]))
            remain_stake = stake - unstake
            stake_part.set_unstakes_info(unstakes_info[i][1], unstake)
            self.assertEqual(remain_stake, stake_part.stake)
            self.assertEqual(0, stake_part.unstake)
            self.assertEqual(0, stake_part.unstake_block_height)
            self.assertEqual(stake_part.unstakes_info, unstakes_info[:i+1])

        # test reducing last unstake
        decrement = 1
        unstake -= decrement
        block_height = UNSTAKE_SLOT_MAX + 100
        stake_part.set_unstakes_info(block_height, unstake)
        expected_unstakes_info = copy.deepcopy(unstakes_info)
        expected_unstakes_info[-1][0] -= decrement
        self.assertEqual(expected_unstakes_info, stake_part.unstakes_info)
        self.assertNotEqual(stake_part.unstakes_info[-1][1], block_height)

        # test increase last unstake
        increment = 1
        unstake += increment
        block_height = UNSTAKE_SLOT_MAX + 1
        stake_part.set_unstakes_info(block_height, unstake)
        expected_unstakes_info[-1][0] += increment
        expected_unstakes_info[-1][1] = block_height
        self.assertEqual(expected_unstakes_info, stake_part.unstakes_info)
        self.assertEqual(stake_part.unstakes_info[-1][1], block_height)

        # test reduce unstake slot
        unstake = sum(map(lambda info: info[0], unstakes_info[:10]))
        stake_part.set_unstakes_info(UNSTAKE_SLOT_MAX, unstake)
        expected_unstakes_info = expected_unstakes_info[:10]
        self.assertEqual(expected_unstakes_info, stake_part.unstakes_info)

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

    def test_stake_part_total_stake_multiple_unstake(self):
        stake = 10
        unstakes_info = [(10, 1), (10, 2)]
        part = StakePart(stake=stake, unstakes_info=unstakes_info)
        part.set_complete(True)
        self.assertEqual(stake+20, part.total_stake)

    def test_stake_part_total_stake_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual(0, part.total_stake)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_unstakes_info(self):
        unstakes_info = [(10, 1), (10, 2)]
        part = StakePart(unstakes_info=unstakes_info)
        part.set_complete(True)
        self.assertEqual(unstakes_info, part.unstakes_info)

    def test_stake_part_unstakes_info_overflow(self):
        part = StakePart()

        with self.assertRaises(Exception) as e:
            self.assertEqual([], part.unstakes_info)
        self.assertEqual(AssertionError, type(e.exception))

    def test_stake_part_total_unstake(self):
        unstake = 10
        part = StakePart(unstake=10)
        part.set_complete(True)
        self.assertEqual(unstake, part.total_unstake)

    def test_stake_part_total_unstake2(self):
        unstakes_info = [(10, 1), (20, 1)]
        part = StakePart(unstakes_info=unstakes_info)
        part.set_complete(True)
        self.assertEqual(30, part.total_unstake)

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
