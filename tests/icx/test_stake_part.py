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
        part1 = StakePart()
        part1.update(0)
        data = part1.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(5, len(data))

        part2 = StakePart.from_bytes(data)
        part2.update(0)
        self.assertEqual(part1.stake, part2.stake)
        self.assertEqual(part1.unstake, part2.unstake)
        self.assertEqual(part1.unstake_block_height, part2.unstake_block_height)

        part3 = StakePart(10, 20, 30)
        part3.update(0)
        part4 = StakePart.from_bytes(part3.to_bytes())
        part4.update(0)
        self.assertEqual(part3.stake, part4.stake)
        self.assertEqual(part3.unstake, part4.unstake)
        self.assertEqual(part3.unstake_block_height, part4.unstake_block_height)

    def test_stake_part_update(self):
        stake: int = 10
        unstake: int = 0
        unstake_block_height: int = 0
        part1 = StakePart(stake, unstake, unstake_block_height)
        part1.update(0)
        self.assertEqual(stake, part1.stake)
        self.assertEqual(unstake, part1.unstake)
        self.assertEqual(unstake_block_height, part1.unstake_block_height)

        stake: int = 5
        unstake: int = 5
        unstake_block_height: int = 3
        part2 = StakePart(stake, unstake, unstake_block_height)
        part2.update(unstake_block_height + 1)
        self.assertEqual(stake, part2.stake)
        self.assertEqual(0, part2.unstake)
        self.assertEqual(0, part2.unstake_block_height)

    def test_stake_part(self):
        stake = 500
        unstake = 0
        unstake_block_height = 0

        stake_part: 'StakePart' = StakePart()
        stake_part.update(0)
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


if __name__ == '__main__':
    unittest.main()
