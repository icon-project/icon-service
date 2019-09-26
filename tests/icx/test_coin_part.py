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
from iconservice.base.exception import InvalidParamsException, OutOfBalanceException
from iconservice.icon_constant import REVISION
from iconservice.icx.base_part import BasePartState
from iconservice.icx.coin_part import CoinPartType, CoinPartFlag, CoinPart
from iconservice.utils import set_flag
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
        part1 = CoinPart()
        self.assertIsNotNone(part1)
        self.assertIs(CoinPartFlag.NONE, part1.flags)
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
        revision = 3

        data = part1.to_bytes(revision)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        part2 = CoinPart.from_bytes(data)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(revision))
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_revision_4(self):
        part1 = CoinPart()

        data = part1.to_bytes(REVISION.FOUR.value)
        self.assertTrue(isinstance(data, bytes))

        part2 = CoinPart.from_bytes(data)
        self.assertEqual(part1, part2)
        self.assertEqual(CoinPartType.GENERAL, part2.type)
        self.assertEqual(0, part2.balance)
        self.assertEqual(CoinPartFlag.NONE, part2.flags)

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(REVISION.FOUR.value))
        self.assertEqual(CoinPartType.GENESIS, part3.type)
        self.assertEqual(1024, part3.balance)

    def test_coin_part_from_bytes_to_bytes_old_db_load_revision_4(self):
        part1 = CoinPart()

        balance = 1024
        part1.type = CoinPartType.GENERAL
        part1.deposit(balance)

        part2 = CoinPart.from_bytes(part1.to_bytes(REVISION.THREE.value))
        self.assertEqual(part1, part2)

        data: bytes = part1.to_bytes(REVISION.FOUR.value)
        part3 = CoinPart.from_bytes(data)
        self.assertEqual(part1, part3)

    def test_coin_part_flag(self):
        part1 = CoinPart()
        self.assertEqual(BasePartState.NONE, part1.states)

        part1._flags = set_flag(part1.flags, CoinPartFlag.HAS_UNSTAKE, True)
        self.assertIn(CoinPartFlag.HAS_UNSTAKE, part1.flags)

        part1._flags = set_flag(part1.flags, CoinPartFlag.HAS_UNSTAKE, False)
        self.assertEqual(CoinPartFlag.NONE, part1.flags)
        self.assertNotIn(CoinPartFlag.HAS_UNSTAKE, part1.flags)

    def test_coin_part_make_key(self):
        key = CoinPart.make_key(create_address())
        self.assertEqual(ICON_EOA_ADDRESS_BYTES_SIZE, len(key))

        key = CoinPart.make_key(create_address(1))
        self.assertEqual(ICON_CONTRACT_ADDRESS_BYTES_SIZE, len(key))

    def test_coin_part_type_property(self):
        part = CoinPart()
        self.assertEqual(CoinPartType.GENERAL, part.type)

        for coin_part_type in CoinPartType:
            part = CoinPart(coin_part_type=coin_part_type)
            self.assertEqual(coin_part_type, part.type)

        for coin_part_type in CoinPartType:
            part = CoinPart()
            part.type = coin_part_type
            self.assertEqual(coin_part_type, part.type)

        with self.assertRaises(ValueError) as e:
            part.type = len(CoinPartType) + 1
        self.assertEqual("Invalid CoinPartType", e.exception.args[0])

    def test_coin_part_balance(self):
        balance = 10000
        part = CoinPart(balance=balance)
        self.assertEqual(balance, part.balance)

    def test_coin_part_flags(self):
        part = CoinPart(flags=CoinPartFlag.HAS_UNSTAKE)
        self.assertEqual(CoinPartFlag.HAS_UNSTAKE, part.flags)

    def test_coin_part_deposit(self):
        balance = 100
        part = CoinPart()

        self.assertFalse(part.is_dirty())
        part.deposit(balance)
        self.assertTrue(part.is_dirty())

        self.assertEqual(balance, part.balance)

    def test_coin_part_withdraw(self):
        balance = 100
        part = CoinPart()

        self.assertFalse(part.is_dirty())
        part.deposit(balance)
        part.withdraw(balance)
        self.assertTrue(part.is_dirty())
        self.assertEqual(0, part.balance)

    def test_coin_part_equal(self):
        part1 = CoinPart()
        part2 = CoinPart()
        self.assertEqual(part1, part2)

        balance = 100
        part1.deposit(balance)
        part3 = CoinPart(balance=balance)
        self.assertEqual(part1, part3)


if __name__ == '__main__':
    unittest.main()
