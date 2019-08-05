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

import shutil
import unittest
from unittest.mock import Mock

from iconservice.base.address import Address, MalformedAddress
from iconservice.base.block import Block
from iconservice.database.db import ContextDatabase
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextType, ContextContainer
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.utils import ContextStorage


class TestIcxEngine(unittest.TestCase, ContextContainer):
    def setUp(self):

        self.db_name = 'engine.db'
        db = ContextDatabase.from_path(self.db_name)
        self.engine = IcxEngine()
        self.storage = IcxStorage(db)
        self.from_ = Address.from_string('hx' + 'a' * 40)
        self.to = Address.from_string('hx' + 'b' * 40)
        self.genesis_address = Address.from_string('hx' + '0' * 40)
        self.fee_treasury_address = Address.from_string('hx' + '1' * 40)
        self.total_supply = 10 ** 20  # 100 icx
        self.fee_treasury_address_icx_amount = 0

        self.context = IconScoreContext(IconScoreContextType.DIRECT)

        block = Mock(spec=Block)
        block.attach_mock(Mock(return_value=0), 'height')
        self.context.block = block

        self.engine.open()

        accounts: list = [
            {'address': self.genesis_address, 'balance': self.total_supply},
            {'address': self.fee_treasury_address, 'balance': 0}
        ]
        self.context.storage = ContextStorage(
            deploy=None,
            fee=None,
            icx=self.storage,
            iiss=None,
            prep=None,
            issue=None,
            rc=None,
            meta=None
        )
        self.storage.put_genesis_accounts(self.context, accounts)

    def tearDown(self):
        self._clear_context()
        self.storage.close(self.context)

        # Remove a state db for test
        shutil.rmtree(self.db_name)

    def test_get_balance(self):
        address = Address.from_string('hx0123456789012345678901234567890123456789')
        balance = self.engine.get_balance(self.context, address)

        self.assertEqual(0, balance)

    def test_get_charge_fee(self):
        pass

    def test_get_account(self):
        pass

    def test_transfer(self):
        context = self.context
        amount = 10 ** 18  # 1 icx
        _from = self.genesis_address

        self.engine.transfer(context=context,
                             from_=_from,
                             to=self.to,
                             amount=amount)

        from_balance = self.engine.get_balance(
            context, self.genesis_address)
        fee_treasury_balance = self.engine.get_balance(
            context, self.fee_treasury_address)
        to_balance = self.engine.get_balance(
            context, self.to)

        self.assertEqual(amount, to_balance)
        self.assertEqual(0, fee_treasury_balance)
        self.assertEqual(
            self.total_supply,
            from_balance + to_balance + fee_treasury_balance)

    # todo: move these tests to test_icx_issue_engine
    # def test_issue(self):
    #     context = self.context
    #     issue_amount = 10 ** 18
    #     to = self.fee_treasury_address
    #
    #     # failure case: when input amount equal 0 or less than 0, should raise AssertionError
    #     for invalid_amount in range(-2, 1):
    #         self.assertRaises(AssertionError, self.engine.issue, context, to, invalid_amount)
    #
    #     # success case: when input amount more than 0, icx should be issued
    #     self.engine.issue(context, to, issue_amount)
    #     actual_total_supply = self.engine.get_total_supply(context)
    #     self.assertEqual(self.total_supply + issue_amount, actual_total_supply)
    #
    #     actual_treasury_icx_amount = self.engine.get_balance(context,
    #                                                          self.fee_treasury_address)
    #
    #     self.assertEqual(self.fee_treasury_address_icx_amount + issue_amount,
    #                      actual_treasury_icx_amount)


class TestIcxEngineForMalformedAddress(unittest.TestCase, ContextContainer):
    def setUp(self):
        empty_address = MalformedAddress.from_string('')
        short_address_without_hx = MalformedAddress.from_string('12341234')
        short_address = MalformedAddress.from_string('hx1234512345')
        long_address_without_hx = MalformedAddress.from_string(
            'cf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf')
        long_address = MalformedAddress.from_string(
            'hxdf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf')
        self.malformed_addresses = [
            empty_address,
            short_address_without_hx, short_address,
            long_address_without_hx, long_address]

        self.db_name = 'engine.db'
        db = ContextDatabase.from_path(self.db_name)
        self.engine = IcxEngine()
        self._from = Address.from_string('hx' + 'a' * 40)
        self.to = Address.from_string('hx' + 'b' * 40)
        self.genesis_address = Address.from_string('hx' + '0' * 40)
        self.fee_treasury_address = Address.from_string('hx' + '1' * 40)
        self.total_supply = 10 ** 20  # 100 icx

        self.context = IconScoreContext(IconScoreContextType.DIRECT)
        block = Mock(spec=Block)
        block.attach_mock(Mock(return_value=0), 'height')
        self.context.block = block

        self.storage = IcxStorage(db)
        self.engine.open()

        accounts: list = [
            {'address': self.genesis_address, 'balance': self.total_supply},
            {'address': self.fee_treasury_address, 'balance': 0}
        ]
        self.context.storage = ContextStorage(
            deploy=None,
            fee=None,
            icx=self.storage,
            iiss=None,
            prep=None,
            issue=None,
            rc=None,
            meta=None
        )
        self.storage.put_genesis_accounts(self.context, accounts)

    def tearDown(self):
        self.storage.close(self.context)
        self.engine = None

        # Remove a state db for test
        shutil.rmtree(self.db_name)

    def test_get_balance(self):
        for address in self.malformed_addresses:
            balance = self.engine.get_balance(self.context, address)
            self.assertEqual(0, balance)

    def test_transfer(self):
        context = self.context
        amount = 10 ** 18  # 1 icx
        from_ = self.genesis_address

        for i, to in enumerate(self.malformed_addresses):
            self.engine.transfer(context=context,
                                 from_=from_,
                                 to=to,
                                 amount=amount)

            from_balance = self.engine.get_balance(context, from_)
            fee_treasury_balance = self.engine.get_balance(
                context, self.fee_treasury_address)
            to_balance = self.engine.get_balance(context, to)

            self.assertEqual(amount, to_balance)
            self.assertEqual(0, fee_treasury_balance)
            self.assertEqual(
                from_balance + fee_treasury_balance + amount * (i + 1),
                self.total_supply)


if __name__ == '__main__':
    unittest.main()
