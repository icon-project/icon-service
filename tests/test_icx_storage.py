#!/usr/bin/env python
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
import shutil

from icx.icx_account import Account
from icx.icx_address import Address
from icx.icx_db import PlyvelDatabase
from icx.icx_storage import IcxStorage


class TestIcxStorage(unittest.TestCase):
    def setUp(self):
        self.db_name = 'icx.db'
        db = PlyvelDatabase(self.db_name)
        self.assertIsNotNone(db)
        self.storage = IcxStorage(db)
        self.address = Address.from_string('hx' + '0' * 40)

    def test_get_put_account(self):
        account = Account()
        account.address = Address.from_string('hx' + '1' * 40)
        account.deposit(10 ** 19)

        self.storage.put_account(account.address, account)

        account2 = self.storage.get_account(account.address)
        self.assertEqual(account, account2)

    def test_delete_account(self):
        account = Account()
        account.address = Address.from_string('hx' + '7' * 40)
        self.storage.put_account(account.address, account)

        ret = self.storage.is_address_present(account.address)
        self.assertTrue(ret)

        self.storage.delete_account(account.address)

        ret = self.storage.is_address_present(self.address)
        self.assertFalse(ret)

    def test_get_put_text(self):
        text = 'hello world'
        self.storage.put_text('text', text)
        text2 = self.storage.get_text('text')

        self.assertEqual(text, text2)

    def tearDown(self):
        self.storage.delete_account(self.address)
        self.storage.close()

        shutil.rmtree(self.db_name)


if __name__ == '__main__':
    unittest.main()
