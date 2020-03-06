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

from unittest.mock import Mock

import pytest

from iconservice.base.address import Address, MalformedAddress
from iconservice.base.block import Block
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.utils import ContextStorage

TOTAL_SUPPLY = 10 ** 20  # 100 icx


@pytest.fixture(scope="function")
def icx_engine():
    engine = IcxEngine()
    engine.open()
    yield engine
    engine.close()


@pytest.fixture(scope="function")
def genesis_address():
    return Address.from_string('hx' + '0' * 40)


@pytest.fixture(scope="function")
def fee_treasury_address():
    return Address.from_string('hx' + '1' * 40)


@pytest.fixture(scope="function")
def context_with_icx_storage(context_db, genesis_address, fee_treasury_address):
    accounts: list = [
        {'address': genesis_address, 'balance': TOTAL_SUPPLY},
        {'address': fee_treasury_address, 'balance': 0}
    ]
    storage = IcxStorage(context_db)
    context = IconScoreContext(IconScoreContextType.DIRECT)
    block = Mock(spec=Block)
    block.attach_mock(Mock(return_value=0), 'height')
    context.block = block
    context.storage = ContextStorage(icx=storage)
    storage.put_genesis_accounts(context, accounts)
    yield context
    storage.close(context)


class TestIcxEngine:
    def test_get_balance(self,
                         context_with_icx_storage,
                         icx_engine):
        address = Address.from_string('hx0123456789012345678901234567890123456789')
        balance = icx_engine.get_balance(context_with_icx_storage, address)

        assert balance == 0

    def test_get_charge_fee(self):
        pass

    def test_get_account(self):
        pass

    def test_transfer(self,
                      context_with_icx_storage,
                      icx_engine,
                      genesis_address,
                      fee_treasury_address):
        context = context_with_icx_storage
        amount = 10 ** 18  # 1 icx
        _from = genesis_address
        to = Address.from_string('hx' + 'b' * 40)

        icx_engine.transfer(context=context,
                            from_=_from,
                            to=to,
                            amount=amount)

        from_balance = icx_engine.get_balance(
            context, genesis_address)
        fee_treasury_balance = icx_engine.get_balance(
            context, fee_treasury_address)
        to_balance = icx_engine.get_balance(
            context, to)

        assert to_balance == amount
        assert fee_treasury_balance == 0
        assert from_balance + to_balance + fee_treasury_balance == TOTAL_SUPPLY


class TestIcxEngineForMalformedAddress:
    MALFORMED_STRING_LIST = [
        '',  # empty
        '12341234',  # short without hx
        'hx1234512345',  # short
        'cf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf',  # long without hx
        'hxdf85fac2d0b507a2db9ce9526e6d01476f16a2d269f51636f9c4b2d512017faf'  # long
    ]

    @pytest.mark.parametrize("malformed_address",
                             [MalformedAddress.from_string(string) for string in MALFORMED_STRING_LIST])
    def test_get_balance(self, context_with_icx_storage, icx_engine, malformed_address):
        balance = icx_engine.get_balance(context_with_icx_storage, malformed_address)
        assert balance == 0

    def test_transfer(self,
                      context_with_icx_storage,
                      icx_engine,
                      genesis_address,
                      fee_treasury_address):
        amount = 10 ** 18  # 1 icx
        for i, to in enumerate([MalformedAddress.from_string(string) for string in self.MALFORMED_STRING_LIST]):
            icx_engine.transfer(context=context_with_icx_storage,
                                from_=genesis_address,
                                to=to,
                                amount=amount)

            from_balance = icx_engine.get_balance(context_with_icx_storage, genesis_address)
            fee_treasury_balance = icx_engine.get_balance(
                context_with_icx_storage, fee_treasury_address)
            to_balance = icx_engine.get_balance(context_with_icx_storage, to)

            assert to_balance == amount
            assert fee_treasury_balance == 0
            assert TOTAL_SUPPLY == from_balance + fee_treasury_balance + amount * (i + 1)
