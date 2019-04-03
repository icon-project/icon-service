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

from iconservice.base.exception import InvalidParamsException, OutOfBalanceException
from iconservice.icon_constant import REVISION_4, REVISION_3
from iconservice.icx.coin_part import CoinPartType, CoinPart, CoinPartFlag
from iconservice.utils import is_flags_on, toggle_flags


class TestAccountType(unittest.TestCase):
    def test_account_type(self):
        self.assertTrue(CoinPartType.GENERAL == 0)
        self.assertTrue(CoinPartType.GENESIS == 1)
        self.assertTrue(CoinPartType.TREASURY == 2)

        self.assertTrue(str(CoinPartType.GENERAL) == 'GENERAL')
        self.assertTrue(str(CoinPartType.GENESIS) == 'GENESIS')
        self.assertTrue(str(CoinPartType.TREASURY) == 'TREASURY')

    def test_from_int(self):
        self.assertEqual(CoinPartType.GENERAL, CoinPartType(0))
        self.assertEqual(CoinPartType.GENESIS, CoinPartType(1))
        self.assertEqual(CoinPartType.TREASURY, CoinPartType(2))

        self.assertRaises(ValueError, CoinPartType, 3)


class TestCoinPart(unittest.TestCase):
    def test_coin_part_revision_3(self):
        part1 = CoinPart()
        self.assertIsNotNone(part1)
        self.assertEqual(CoinPartFlag.NONE, part1.flags)
        self.assertTrue(part1.balance == 0)

        part1.deposit(100)
        self.assertEqual(100, part1.balance)

        part1.withdraw(100)
        self.assertEqual(0, part1.balance)

        # wrong value
        self.assertRaises(InvalidParamsException, part1.deposit, -10)

        # 0 transfer is possible
        old = part1.balance
        part1.deposit(0)
        self.assertEqual(old, part1.balance)

        self.assertRaises(InvalidParamsException, part1.withdraw, -11234)
        self.assertRaises(OutOfBalanceException, part1.withdraw, 1)

        old = part1.balance
        part1.withdraw(0)
        self.assertEqual(old, part1.balance)

    def test_coin_part_from_bytes_to_bytes_revision_3(self):
        part1 = CoinPart()

        data = part1.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        part2 = CoinPart.from_bytes(data)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes())
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_revision_4(self):
        part1 = CoinPart()

        data = part1.to_bytes(REVISION_4)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(11, len(data))

        part2 = CoinPart.from_bytes(data)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(REVISION_4))
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_old_db_load_revision_4(self):
        part1 = CoinPart()

        balance = 1024
        part1.type = CoinPartType.GENERAL
        part1.deposit(balance)

        part2 = CoinPart.from_bytes(part1.to_bytes(REVISION_3))
        self.assertEqual(part1, part2)

        data: bytes = part1.to_bytes(REVISION_4)
        part3 = CoinPart.from_bytes(data)
        self.assertEqual(part1, part3)

    def test_coin_part_flag(self):
        part1 = CoinPart()
        self.assertEqual(True, is_flags_on(part1.flags, CoinPartFlag.NONE))

        part1._flags = toggle_flags(part1.flags, CoinPartFlag.HAS_UNSTAKE, True)
        self.assertEqual(True, is_flags_on(part1.flags, CoinPartFlag.HAS_UNSTAKE))

        part1._flags = toggle_flags(part1.flags, CoinPartFlag.HAS_UNSTAKE, False)
        self.assertEqual(True, is_flags_on(part1.flags, CoinPartFlag.NONE))


if __name__ == '__main__':
    unittest.main()
