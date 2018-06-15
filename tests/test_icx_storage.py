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

from iconservice.base.address import Address, AddressPrefix
from iconservice.database.db import ContextDatabase
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.icx.icx_account import Account
from iconservice.icx.icx_storage import IcxStorage
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContextFactory


class TestIcxStorage(unittest.TestCase):
    def setUp(self):
        self.db_name = 'icx.db'
        self.address = Address.from_string('hx' + '0' * 40)
        db = ContextDatabase.from_address_and_path(self.address, self.db_name)
        self.assertIsNotNone(db)

        self.storage = IcxStorage(db)

        self.factory = IconScoreContextFactory(max_size=1)
        context = self.factory.create(IconScoreContextType.GENESIS)
        context.tx_batch = TransactionBatch()
        context.block_batch = BlockBatch()
        self.context = context

    def test_get_put_account(self):
        context = self.context
        account = Account()
        account.address = Address.from_string('hx' + '1' * 40)
        account.deposit(10 ** 19)

        self.storage.put_account(context, account.address, account)

        account2 = self.storage.get_account(context, account.address)
        self.assertEqual(account, account2)

    def test_delete_account(self):
        context = self.context
        account = Account()
        account.address = Address.from_string('hx' + '7' * 40)
        self.storage.put_account(context, account.address, account)

        ret = self.storage.is_address_present(context, account.address)
        self.assertTrue(ret)

        self.storage.delete_account(context, account.address)

        ret = self.storage.is_address_present(context, self.address)
        self.assertFalse(ret)

    def test_get_put_text(self):
        context = self.context
        text = 'hello world'
        self.storage.put_text(context, 'text', text)
        text2 = self.storage.get_text(context, 'text')

        self.assertEqual(text, text2)

    def test_owner(self):
        context = self.context
        icon_score_address = Address.from_data(
            AddressPrefix.CONTRACT, b'score')
        owner = Address.from_data(AddressPrefix.EOA, b'owner')

        self.storage.put_score_owner(context, icon_score_address, owner)

        owner2 = self.storage.get_score_owner(context, icon_score_address)
        self.assertTrue(isinstance(owner2, Address))
        self.assertEqual(AddressPrefix.EOA, owner2.prefix)
        self.assertEqual(owner, owner2)

    def test_is_score_installed(self):
        context = self.context
        icon_score_address = Address.from_data(
            AddressPrefix.CONTRACT, b'score')
        owner = Address.from_data(AddressPrefix.EOA, b'owner')

        installed = self.storage.is_score_installed(context,
                                                    icon_score_address)
        self.assertFalse(installed)

        self.storage.put_score_owner(context, icon_score_address, owner)

        installed = self.storage.is_score_installed(context,
                                                    icon_score_address)
        self.assertTrue(installed)

    def tearDown(self):
        context = self.context
        self.storage.delete_account(context, self.address)
        self.storage.close(context)

        shutil.rmtree(self.db_name)


if __name__ == '__main__':
    unittest.main()
