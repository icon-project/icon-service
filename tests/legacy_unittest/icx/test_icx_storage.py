#!/usr/bin/env python
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

import json
import shutil
import unittest

from typing import TYPE_CHECKING
from unittest.mock import Mock

from iconservice.base.block import Block
from iconservice.base.address import AddressPrefix, MalformedAddress
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.database.db import ContextDatabase
from iconservice.iconscore.icon_score_context import (
    IconScoreContextType,
    IconScoreContext,
)
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.icx_account import Account
from iconservice.icx import IcxStorage
from tests import create_address

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIcxStorage(unittest.TestCase):
    def setUp(self):
        self.db_name = "icx.db"

        db = ContextDatabase.from_path(self.db_name)
        self.assertIsNotNone(db)

        self.storage = IcxStorage(db)

        context = IconScoreContext(IconScoreContextType.DIRECT)
        context.tx_batch = TransactionBatch()
        mock_block: "Mock" = Mock(spec=Block)
        mock_block.attach_mock(Mock(return_value=0), "height")
        context.block = mock_block
        context.block_batch = BlockBatch()
        self.context = context

    def tearDown(self):
        context = self.context
        self.storage.close(context)

        shutil.rmtree(self.db_name)

    def test_get_put_account(self):
        context = self.context

        address = create_address(AddressPrefix.EOA)
        coin_part: "CoinPart" = CoinPart()
        account: "Account" = Account(address, 0, coin_part=coin_part)
        account.deposit(10 ** 19)

        self.storage.put_account(context, account)

        address: "Address" = create_address(AddressPrefix.EOA)
        coin_part: "CoinPart" = CoinPart()
        account: "Account" = Account(
            address, self.context.block.height, coin_part=coin_part
        )

        account.deposit(10 ** 19)

        self.storage.put_account(self.context, account)

        account2 = self.storage.get_account(self.context, account.address)
        self.assertEqual(account, account2)

    def test_get_put_text(self):
        context = self.context
        key_name = "test_genesis"
        expected_text = json.dumps(
            {"version": 0, "address": str(create_address(AddressPrefix.EOA))}
        )

        self.storage.put_text(context, key_name, expected_text)

        actual_stored_text = self.storage.get_text(context, key_name)
        self.assertEqual(expected_text, actual_stored_text)

    def test_get_put_total_supply(self):
        context = self.context
        current_total_supply = self.storage.get_total_supply(context)
        self.assertEqual(0, current_total_supply)

        putting_total_supply_amount = 1000
        self.storage.put_total_supply(context, putting_total_supply_amount)
        actual_stored_total_supply = self.storage.get_total_supply(context)
        self.assertEqual(putting_total_supply_amount, actual_stored_total_supply)


class TestIcxStorageForMalformedAddress(unittest.TestCase):
    def setUp(self):
        empty_address = MalformedAddress.from_string("")
        short_address_without_hx = MalformedAddress.from_string("12341234")
        short_address = MalformedAddress.from_string("hx1234512345")
        long_address_without_hx = MalformedAddress.from_string(
            "cf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf"
        )
        long_address = MalformedAddress.from_string(
            "hxcf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf"
        )
        self.addresses = [
            empty_address,
            short_address_without_hx,
            short_address,
            long_address_without_hx,
            long_address,
        ]

        self.db_name = "icx.db"
        db = ContextDatabase.from_path(self.db_name)
        self.assertIsNotNone(db)

        self.storage = IcxStorage(db)

        context = IconScoreContext(IconScoreContextType.DIRECT)
        mock_block: "Mock" = Mock(spec=Block)
        mock_block.attach_mock(Mock(return_value=0), "height")
        context.block = mock_block

        self.context = context

    def tearDown(self):
        context = self.context
        self.storage.close(context)

        shutil.rmtree(self.db_name)

    def test_get_put_account(self):
        accounts: list = []
        for address in self.addresses:
            coin_part: "CoinPart" = CoinPart()
            account: "Account" = Account(
                address, self.context.block.height, coin_part=coin_part
            )
            account.deposit(10 ** 19)
            accounts.append(account)

        for account in accounts:
            self.storage.put_account(self.context, account)
            account2 = self.storage.get_account(self.context, account.address)
            self.assertEqual(account, account2)


if __name__ == "__main__":
    unittest.main()
