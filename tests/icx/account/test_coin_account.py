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
from iconservice.icx.coin_part import CoinPartType, CoinPart
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
        self.assertEqual(CoinPartType.GENERAL, CoinPartType.from_int(0))
        self.assertEqual(CoinPartType.GENESIS, CoinPartType.from_int(1))
        self.assertEqual(CoinPartType.TREASURY, CoinPartType.from_int(2))

        self.assertRaises(ValueError, CoinPartType.from_int, 3)


class TestCoinPart(unittest.TestCase):
    def test_coin_part_revision_3(self):
        address: 'Address' = create_address()

        account1 = CoinPart(address)
        self.assertIsNotNone(account1)
        self.assertEqual(address, account1.address)
        self.assertTrue(account1.balance == 0)

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

    def test_coin_part_from_bytes_to_bytes_revision_3(self):
        address: 'Address' = create_address()

        account = CoinPart(address)

        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        account2 = CoinPart.from_bytes(data, address)
        self.assertFalse(account2.locked)
        self.assertEqual(CoinPartType.GENERAL, account2.type)
        self.assertEqual(0, account2.balance)

        account.type = CoinPartType.GENESIS
        account.deposit(1024)

        account3 = CoinPart.from_bytes(account.to_bytes(), address)
        self.assertEqual(CoinPartType.GENESIS, account3.type)
        self.assertEqual(1024, account3.balance)

    def test_account_from_bytes_to_bytes_revision_4(self):
        address: 'Address' = create_address()

        account = CoinPart(address)

        data = account.to_bytes(REVISION_4)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(9, len(data))

        account2 = CoinPart.from_bytes(data, address)
        self.assertFalse(account2.locked)
        self.assertEqual(CoinPartType.GENERAL, account2.type)
        self.assertEqual(0, account2.balance)

        account.type = CoinPartType.GENESIS
        account.deposit(1024)

        account3 = CoinPart.from_bytes(account.to_bytes(REVISION_4), address)
        self.assertEqual(CoinPartType.GENESIS, account3.type)
        self.assertEqual(1024, account3.balance)

    def test_account_from_bytes_to_bytes_old_db_load_revision_4(self):
        address: 'Address' = create_address()

        account = CoinPart(address)

        balance = 1024
        account.type = CoinPartType.GENERAL
        account.deposit(balance)

        account1 = CoinPart.from_bytes(account.to_bytes(REVISION_3), address)
        self.assertEqual(account, account1)

        data: bytes = account.to_bytes(REVISION_4)
        account2 = CoinPart.from_bytes(data, address)
        self.assertEqual(account, account2)


if __name__ == '__main__':
    unittest.main()
