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

import logging
import unittest
import shutil

from iconservice.base.address import Address
from iconservice.database.db import PlyvelDatabase
from iconservice.icx.icx_config import FIXED_FEE
from iconservice.icx.icx_error import IcxError
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_account import Account
from iconservice.icx.icx_logger import IcxLogger
from iconservice.icx.icx_storage import IcxStorage


class TestIcxEngine(unittest.TestCase):
    def setUp(self):
        self.db_name = 'engine.db'
        db = PlyvelDatabase(self.db_name)
        self.engine = IcxEngine()
        self._from = Address.from_string('hx' + 'a' * 40)
        self.to = Address.from_string('hx' + 'b' * 40)
        self.genesis_address = Address.from_string('hx' + '0' * 40)
        self.fee_treasury_address = Address.from_string('hx' + '1' * 40)
        self.total_supply = 10 ** 20  # 100 icx

        logger = IcxLogger()
        self.engine.open(db, logger)

        self.engine.init_genesis_account(self.genesis_address, self.total_supply)
        self.engine.init_fee_treasury_account(self.fee_treasury_address, 0)

    def tearDown(self):
        self.engine.close()
        self.engine = None

        # Remove a state db for test
        shutil.rmtree(self.db_name)

    def test_get_balance(self):
        address = Address.from_string('hx0123456789012345678901234567890123456789')
        balance = self.engine.get_balance(address)

        self.assertEqual(0, balance)

    def test_get_total_supply(self):
        total_supply = self.engine.get_total_supply()

        self.assertEqual(self.total_supply, total_supply)

    def test_transfer(self):
        amount = 10 ** 18  # 1 icx
        _from = self.genesis_address

        self.engine.transfer(_from, self.to, amount, FIXED_FEE)

        from_balance = self.engine.get_balance(self.genesis_address)
        fee_treasury_balance = self.engine.get_balance(self.fee_treasury_address)
        to_balance = self.engine.get_balance(self.to)

        self.assertEqual(amount, to_balance)
        self.assertEqual(FIXED_FEE, fee_treasury_balance)
        self.assertEqual(
            self.total_supply,
            from_balance + to_balance + fee_treasury_balance)


if __name__ == '__main__':
    unittest.main()
