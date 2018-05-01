#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from iconservice.base.address import Address
from iconservice.base.exception import IconException
from iconservice.icx.icx_account import AccountType, Account


class TestAccountType(unittest.TestCase):
    def test_account_type(self):
        self.assertTrue(AccountType.GENERAL == 0)
        self.assertTrue(AccountType.GENESIS == 1)
        self.assertTrue(AccountType.TREASURY == 2)
        self.assertTrue(AccountType.CONTRACT == 3)

        self.assertTrue(str(AccountType.GENERAL) == 'GENERAL')
        self.assertTrue(str(AccountType.GENESIS) == 'GENESIS')
        self.assertTrue(str(AccountType.TREASURY) == 'TREASURY')
        self.assertTrue(str(AccountType.CONTRACT) == 'CONTRACT')

    def test_from_int(self):
        self.assertEqual(AccountType.GENERAL, AccountType.from_int(0))
        self.assertEqual(AccountType.GENESIS, AccountType.from_int(1))
        self.assertEqual(AccountType.TREASURY, AccountType.from_int(2))
        self.assertEqual(AccountType.CONTRACT, AccountType.from_int(3))

        self.assertRaises(ValueError, AccountType.from_int, 4)


class TestAccount(unittest.TestCase):
    def test_account(self):
        account1 = Account()
        self.assertIsNotNone(account1)
        self.assertIsNone(account1.address)
        self.assertTrue(account1.icx == 0)
        self.assertFalse(account1.locked)
        self.assertFalse(account1.c_rep)

        text = 'hx00678792645ed9f18f1560c4b2e1b0aa028f61e4'
        account1.address = Address.from_string(text)

        account1.deposit(100)
        self.assertEqual(100, account1.icx)

        account1.withdraw(100)
        self.assertEqual(0, account1.icx)

        # wrong value
        self.assertRaises(IconException, account1.deposit, -10)
        self.assertRaises(IconException, account1.deposit, 0)

        self.assertRaises(IconException, account1.withdraw, -11234)
        self.assertRaises(IconException, account1.withdraw, 0)
        self.assertRaises(IconException, account1.withdraw, 1)

    def test_account_from_bytes_to_bytes(self):
        account = Account()

        data = account.to_bytes()
        self.assertEqual(bytes(account), data)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(36, len(data))

        account2 = Account.from_bytes(data)
        self.assertFalse(account2.locked)
        self.assertFalse(account2.c_rep)
        self.assertEqual(AccountType.GENERAL, account2.type)
        self.assertEqual(0, account2.icx)

        account.type = AccountType.GENESIS
        account.locked = True
        account.c_rep = True
        account.deposit(1024)

        account3 = Account.from_bytes(account.to_bytes())
        self.assertTrue(account3.locked)
        self.assertTrue(account3.c_rep)
        self.assertEqual(AccountType.GENESIS, account3.type)
        self.assertEqual(1024, account3.icx)


if __name__ == '__main__':
    unittest.main()
