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
from iconservice.icx.coin_part import CoinPartType, CoinPart, CoinPartFlag
from tests import create_address


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
        address: 'Address' = create_address()

        part1 = CoinPart(address)
        self.assertIsNotNone(part1)
        self.assertEqual(CoinPartFlag.NONE, part1.flag)
        self.assertEqual(address, part1.address)
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
        address: 'Address' = create_address()

        part1 = CoinPart(address)

        data = part1.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        part2 = CoinPart.from_bytes(data, address)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(), address)
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_revision_4(self):
        address: 'Address' = create_address()

        part1 = CoinPart(address)

        data = part1.to_bytes(REVISION_4)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(11, len(data))

        part2 = CoinPart.from_bytes(data, address)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(REVISION_4), address)
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_old_db_load_revision_4(self):
        address: 'Address' = create_address()

        part1 = CoinPart(address)

        balance = 1024
        part1.type = CoinPartType.GENERAL
        part1.deposit(balance)

        account1 = CoinPart.from_bytes(part1.to_bytes(REVISION_3), address)
        self.assertEqual(part1, account1)

        data: bytes = part1.to_bytes(REVISION_4)
        account2 = CoinPart.from_bytes(data, address)
        self.assertEqual(part1, account2)

    def test_coin_part_flag(self):
        address: 'Address' = create_address()

        part1 = CoinPart(address)
        self.assertEqual(True, part1.is_flag_on(CoinPartFlag.NONE))

        part1.toggle_flag(CoinPartFlag.HAS_UNSTAKE, True)
        self.assertEqual(True, part1.is_flag_on(CoinPartFlag.HAS_UNSTAKE))

        part1.toggle_flag(CoinPartFlag.HAS_UNSTAKE, False)
        self.assertEqual(True, part1.is_flag_on(CoinPartFlag.NONE))


if __name__ == '__main__':
    unittest.main()
