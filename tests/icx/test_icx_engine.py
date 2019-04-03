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

import json
import shutil
import unittest
from unittest.mock import Mock

from iconservice.base.block import Block
from iconservice.base.address import Address, MalformedAddress
from iconservice.database.db import ContextDatabase
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextType, ContextContainer
from iconservice.icx.coin_part import CoinPartType, CoinPart
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage, AccountPartFlag
from iconservice.icx.icx_account import Account, PartFlag


class TestIcxEngine(unittest.TestCase, ContextContainer):
    def setUp(self):

        self.db_name = 'engine.db'
        db = ContextDatabase.from_path(self.db_name)
        self.engine = IcxEngine()
        self.from_ = Address.from_string('hx' + 'a' * 40)
        self.to = Address.from_string('hx' + 'b' * 40)
        self.genesis_address = Address.from_string('hx' + '0' * 40)
        self.fee_treasury_address = Address.from_string('hx' + '1' * 40)
        self.total_supply = 10 ** 20  # 100 icx

        self.context = IconScoreContext(IconScoreContextType.DIRECT)

        block = Mock(spec=Block)
        block.attach_mock(Mock(return_value=0), 'height')
        self.context.block = block

        icx_storage = IcxStorage(db)
        self.engine.open(icx_storage)

        accounts: list = [
            {'address': self.genesis_address, 'balance': self.total_supply},
            {'address': self.fee_treasury_address, 'balance': 0}
        ]
        self.engine.put_genesis_accounts(self.context, accounts)

    def tearDown(self):
        self._clear_context()
        self.engine.close()

        # Remove a state db for test
        shutil.rmtree(self.db_name)

    def test_put_genesis_data_account(self):
        def intercept_storage_put_account(context: 'IconScoreContext', account: 'Account'):
            if not isinstance(account, Account):
                raise Exception("invalid type of params was set when calling put_account")

        self.engine._storage.put_account = Mock(side_effect=intercept_storage_put_account)

        # genesis
        self.engine._put_special_account = Mock()
        genesis_address = Address.from_string('hx' + 'f' * 40)
        self.engine._put_genesis_data_account(
            self.context, CoinPartType.GENESIS, genesis_address, 1000)
        self.total_supply += 1000

        self.engine._storage.put_account.assert_called()
        self.engine._put_special_account.assert_called()
        self.assertEqual(self.total_supply, self.engine._total_supply_amount)

        # general
        self.engine._put_special_account = Mock()
        self.engine._init_special_account = Mock()
        general_addr = Address.from_string('hx' + 'f' * 40)
        self.engine._put_genesis_data_account(
            self.context, CoinPartType.GENERAL, general_addr, 1000)
        self.total_supply += 1000

        self.engine._storage.put_account.assert_called()
        self.engine._put_special_account.assert_not_called()
        self.assertEqual(self.total_supply, self.engine._total_supply_amount)

    def test_put_special_account(self):
        # failure case: input general account
        account = Mock(spec=Account)
        coin_part = Mock(spec=CoinPart)
        coin_part.attach_mock(CoinPartType.GENERAL, 'type')
        account.attach_mock(coin_part, 'coin_part')

        self.assertRaises(AssertionError,
                          self.engine._put_special_account, self.context, account)

        # success case: input genesis and treasury account
        account = Mock(spec=Account)
        coin_part = Mock(spec=CoinPart)
        coin_part.attach_mock(CoinPartType.GENESIS, 'type')
        account.attach_mock(coin_part, 'coin_part')

        self.engine._put_special_account(self.context, account)
        self.assertEqual(account.address, self.engine._genesis_address)

        account = Mock(spec=Account)
        coin_part = Mock(spec=CoinPart)
        coin_part.attach_mock(CoinPartType.TREASURY, 'type')
        account.attach_mock(coin_part, 'coin_part')

        self.engine._put_special_account(self.context, account)
        self.assertEqual(account.address, self.engine._fee_treasury_address)

        def intercept_storage_put_text(*args, **kwargs):
            text = args[-1]
            text_dict = json.loads(text)

            expected_version = 0
            expected_address = str(account.address)
            self.assertEqual(expected_version, text_dict['version'])
            self.assertEqual(expected_address, text_dict['address'])

        self.engine.storage.put_text = Mock(side_effect=intercept_storage_put_text)
        self.engine._put_special_account(self.context, account)
        self.engine.storage.put_text.assert_called()

    def test_load_address_from_storage(self):
        # success case: when stored genesis address is exist
        genesis_address = Address.from_string('hx' + 'f' * 40)
        expected_text = {'version': 0, 'address': str(genesis_address)}

        # make mock which returns stringified json data
        icx_storage_mock = Mock(spec=IcxStorage)
        icx_storage_mock.get_text = Mock(return_value=json.dumps(expected_text))

        self.engine._load_address_from_storage(self.context,
                                               icx_storage_mock,
                                               self.engine._GENESIS_DB_KEY)

        # check genesis_address
        self.assertEqual(genesis_address, self.engine._genesis_address)

        # success case: when stored genesis address is not exist
        # reset icx engine's genesis address
        self.engine._genesis_address = None
        icx_storage_mock.get_text = Mock(return_value=None)

        self.engine._load_address_from_storage(self.context,
                                               icx_storage_mock,
                                               self.engine._GENESIS_DB_KEY)
        self.assertEqual(None, self.engine._genesis_address)

    def test_load_total_supply_amount_from_storage(self):
        pass

    def test_get_balance(self):
        address = Address.from_string('hx0123456789012345678901234567890123456789')
        balance = self.engine.get_balance(self.context, address)

        self.assertEqual(0, balance)

    def test_get_total_supply(self):
        total_supply = self.engine.get_total_supply(self.context)

        self.assertEqual(self.total_supply, total_supply)

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
    
        icx_storage = IcxStorage(db)
        self.engine.open(icx_storage)

        accounts: list = [
            {'address': self.genesis_address, 'balance': self.total_supply},
            {'address': self.fee_treasury_address, 'balance': 0}
        ]
        self.engine.put_genesis_accounts(self.context, accounts)

    def tearDown(self):
        self.engine.close()
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
