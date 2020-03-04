# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

import random
import unittest
from collections import OrderedDict
from typing import TYPE_CHECKING, List, Tuple, Dict, Optional
from unittest.mock import Mock

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException, InvalidRequestException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_DAY_BLOCK
from iconservice.icon_constant import IISS_MAX_DELEGATIONS
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.coin_part import CoinPart
from iconservice.icx.delegation_part import DelegationPart
from iconservice.icx.icx_account import Account
from iconservice.icx.stake_part import StakePart
from iconservice.icx.storage import Intent, AccountPartFlag
from iconservice.iiss import IISSEngine, IISSEngineListener
from iconservice.utils import icx_to_loop

if TYPE_CHECKING:
    pass


EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT = [
    864000, 845618, 827500, 809647, 792059,
    774735, 757675, 740880, 724349, 708083,
    692082, 676344, 660872, 645664, 630720,
    616041, 601626, 587476, 573590, 559969,
    546612, 533520, 520692, 508129, 495830,
    483796, 472026, 460521, 449280, 438304,
    427592, 417144, 406962, 397043, 387389,
    378000, 368875, 360015, 351419, 343087,
    335020, 327218, 319680, 312407, 305398,
    298653, 292173, 285958, 280007, 274320,
    268898, 263740, 258847, 254219, 249855,
    245755, 241920, 238349, 235043, 232002,
    229224, 226712, 224464, 222480, 220761,
    219306, 218116, 217190, 216529, 216132,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000
]


SENDER_ADDRESS = Address.from_prefix_and_int(AddressPrefix.EOA, 0)


def create_account(
        address: 'Address', balance: int,
        stake: int, unstake: int, unstake_block_height: int,
        delegated_amount: int, delegations: List[Tuple[Address, int]]) -> 'Account':
    coin_part = CoinPart(balance=balance)
    stake_part = StakePart(stake, unstake, unstake_block_height)
    delegation_part = DelegationPart(delegated_amount, delegations)

    return Account(
        address, 1024,
        coin_part=coin_part,
        stake_part=stake_part,
        delegation_part=delegation_part)


def create_sender_account(stake: int):
    total_delegating = 0
    old_delegations: List[Tuple['Address', int], ...] = []

    for i in range(IISS_MAX_DELEGATIONS):
        value = i + 1
        address = Address.from_prefix_and_int(AddressPrefix.EOA, value)
        old_delegations.append((address, value))
        total_delegating += value

    sender_address = SENDER_ADDRESS
    return create_account(
        address=sender_address, balance=icx_to_loop(10),
        stake=stake, unstake=0, unstake_block_height=0,
        delegated_amount=0, delegations=old_delegations)


def get_account(context: 'IconScoreContext',
                address: 'Address',
                intent: 'Intent' = Intent.TRANSFER) -> 'Account':

    """Returns the account indicated by address.

    :param context:
    :param address: account address
    :param intent:
    :return: (Account)
        If the account indicated by address is not present,
        create a new account.
    """
    if address == SENDER_ADDRESS:
        return create_sender_account(stake=10_000)

    coin_part: Optional['CoinPart'] = None
    stake_part: Optional['StakePart'] = None
    delegation_part: Optional['DelegationPart'] = None

    part_flags: 'AccountPartFlag' = AccountPartFlag(intent)

    if AccountPartFlag.COIN in part_flags:
        coin_part: 'CoinPart' = CoinPart(balance=0)

    if AccountPartFlag.STAKE in part_flags:
        stake_part = StakePart(0, 0, 0)

    if AccountPartFlag.DELEGATION in part_flags:
        value: int = int.from_bytes(address.body, "big")
        delegated_amount = value if 1 <= value <= 10 else 0
        delegation_part = DelegationPart(delegated_amount=delegated_amount)

    return Account(address, context.block.height,
                   coin_part=coin_part,
                   stake_part=stake_part,
                   delegation_part=delegation_part)


def create_delegations_param() -> Tuple[int, Dict]:
    params = {}
    delegations = []
    total_delegating = 0

    for i in range(IISS_MAX_DELEGATIONS):
        _id = i + 11
        address = Address.from_prefix_and_int(AddressPrefix.EOA, _id)
        value = _id

        delegations.append({
            "address": str(address),
            "value": hex(value)
        })
        total_delegating += value

    params[ConstantKeys.DELEGATIONS] = delegations

    return total_delegating, params


class TestIissEngine(unittest.TestCase):
    def test_calculate_unstake_lock_period(self):
        lmin = IISS_DAY_BLOCK * 5
        lmax = IISS_DAY_BLOCK * 20
        rpoint = 7000
        for x in range(0, 100):
            ret = IISSEngine._calculate_unstake_lock_period(lmin, lmax, rpoint, x, 100)
            diff = abs(ret - EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT[x])
            assert diff <= 1

    def test__convert_params_of_set_delegation_ok(self):
        params = {}
        delegations = []
        total_delegating = 0

        for i in range(IISS_MAX_DELEGATIONS):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, i + 1)
            value = random.randint(1, 10_000)

            delegations.append({
                "address": str(address),
                "value": hex(value)
            })
            total_delegating += value

        params[ConstantKeys.DELEGATIONS] = delegations

        ret_total_delegating, ret_delegations = IISSEngine._convert_params_of_set_delegation(params)
        assert ret_total_delegating == total_delegating

        for i in range(len(delegations)):
            item: Tuple['Address', int] = ret_delegations[i]
            address: 'Address' = item[0]
            value: int = item[1]

            assert str(address) == delegations[i]["address"]
            assert hex(value) == delegations[i]["value"]

    def test__convert_params_of_set_delegation_with_value_0(self):
        params = {}
        delegations = []
        total_delegating = 0

        for i in range(IISS_MAX_DELEGATIONS):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, i + 1)
            value = 0 if i < 5 else i + 1

            delegations.append({
                "address": str(address),
                "value": hex(value)
            })
            total_delegating += value

        params[ConstantKeys.DELEGATIONS] = delegations

        ret_total_delegating, ret_delegations = IISSEngine._convert_params_of_set_delegation(params)
        assert ret_total_delegating == total_delegating == (6 + 7 + 8 + 9 + 10)
        assert len(ret_delegations) == 5

        i = 5
        # 5 delegations including 0 value were dropped.
        for address, value in ret_delegations:
            delegation: Dict[str, Optional[str, int]] = delegations[i]
            assert str(address) == delegation["address"]
            assert hex(value) == delegation["value"]
            i += 1

    def test__convert_params_of_set_delegation_with_value_less_than_0(self):
        params = {}
        delegations = []

        values = [1, 2, 3, 4, -100]

        for i in range(5):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, i + 1)
            value = values[i]

            delegations.append({
                "address": str(address),
                "value": hex(value)
            })

        params[ConstantKeys.DELEGATIONS] = delegations

        with pytest.raises(InvalidParamsException):
            IISSEngine._convert_params_of_set_delegation(params)

    def test__convert_params_of_set_delegation_with_duplicate_address(self):
        params = {}
        delegations = []

        for i in range(2):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, 1)
            value = random.randint(1, 100)

            delegations.append({
                "address": str(address),
                "value": hex(value)
            })

        params[ConstantKeys.DELEGATIONS] = delegations

        with pytest.raises(InvalidParamsException):
            IISSEngine._convert_params_of_set_delegation(params)

    def test__convert_params_of_set_delegation_with_too_many_delegations(self):
        params = {}
        delegations = []

        for i in range(IISS_MAX_DELEGATIONS + 1):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, i + 1)
            value = random.randint(1, 10_000)

            delegations.append({
                "address": str(address),
                "value": hex(value)
            })

        params[ConstantKeys.DELEGATIONS] = delegations

        with pytest.raises(InvalidParamsException):
            IISSEngine._convert_params_of_set_delegation(params)

    def test__check_voting_power_is_enough(self):
        def _get_account(_context: 'IconScoreContext',
                         _address: 'Address',
                         _intent: 'Intent' = Intent.TRANSFER) -> 'Account':
            return create_sender_account(stake=155)

        cached_accounts: Dict['Address', Tuple['Account', int]] = {}
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=_get_account)
        total_delegating = sum(range(11, 21))  # new_delegations

        IISSEngine._check_voting_power_is_enough(
            context, SENDER_ADDRESS, total_delegating, cached_accounts)

        sender_item: Tuple['Account', int] = cached_accounts[SENDER_ADDRESS]

        assert len(cached_accounts) == 1
        assert sender_item[0] == _get_account(context, SENDER_ADDRESS, Intent.ALL)
        assert sender_item[1] == 0  # delegated_amount_offset
        assert sender_item[0].delegations_amount == sum(range(1, 11))  # old delegations
        assert sender_item[0].stake >= total_delegating

    def test__check_voting_power_is_enough_with_not_enough_stake(self):
        def _get_account(_context: 'IconScoreContext',
                         _address: 'Address',
                         _intent: 'Intent' = Intent.TRANSFER) -> 'Account':
            return create_sender_account(stake=100)

        cached_accounts: Dict['Address', Tuple['Account', int]] = {}
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=_get_account)
        total_delegating = sum(range(11, 21))  # new_delegations

        with pytest.raises(InvalidRequestException):
            IISSEngine._check_voting_power_is_enough(
                context, SENDER_ADDRESS, total_delegating, cached_accounts)

    def test__get_old_delegations_from_sender_account(self):
        cached_accounts: Dict['Address', Tuple['Account', int]] = {}
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=get_account)

        sender_account = context.storage.icx.get_account(context, SENDER_ADDRESS, Intent.ALL)
        cached_accounts[SENDER_ADDRESS] = sender_account, 0

        # Get old delegations from delegating accounts
        IISSEngine._get_old_delegations_from_sender_account(context, SENDER_ADDRESS, cached_accounts)
        assert len(cached_accounts) == 11  # sender_account(1) + old delegated_accounts(10)

        for i, address in enumerate(cached_accounts):
            item: Tuple['Account', int] = cached_accounts[address]
            account = item[0]
            delegated_offset = item[1]

            assert address == account.address

            if i == 0:
                assert delegated_offset == 0
            else:
                delegation: Tuple['Account', int] = sender_account.delegations[i - 1]
                assert address == delegation[0]
                assert delegated_offset == -delegation[1]

    def test__calc_delegations(self):
        cached_accounts: Dict['Address', Tuple['Account', int]] = OrderedDict()
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=get_account)

        new_delegations: List[Tuple['Address', int]] = []
        for i in range(10):
            value: int = i + 11
            address = Address.from_prefix_and_int(AddressPrefix.EOA, value)
            new_delegations.append((address, value))

        sender_account = context.storage.icx.get_account(context, SENDER_ADDRESS, Intent.ALL)
        cached_accounts[SENDER_ADDRESS] = sender_account, 0

        # Prepare old delegations
        for i in range(10):
            value: int = i + 1
            address = Address.from_prefix_and_int(AddressPrefix.EOA, value)
            account = context.storage.icx.get_account(context, address, Intent.DELEGATED)
            cached_accounts[address] = account, -value

        IISSEngine._calc_delegations(context, new_delegations, cached_accounts)
        # 0: sender_account, 1~10: old_accounts 11~20: new_accounts

        for i, address in enumerate(cached_accounts):
            account, delegated_offset = cached_accounts[address]
            assert account.address == address

            if i == 0:
                assert address == SENDER_ADDRESS
                assert delegated_offset == 0
            elif 1 <= i <= 10:
                assert delegated_offset == -i
            else:  # 11 <= i <= 20
                assert delegated_offset == i

    def test__put_delegation_to_state_db(self):
        cached_accounts: Dict['Address', Tuple['Account', int]] = OrderedDict()
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=get_account)

        total_delegating = 0
        new_delegations: List[Tuple['Address', int]] = []
        for i in range(10):
            value: int = i + 11
            address = Address.from_prefix_and_int(AddressPrefix.EOA, value)
            new_delegations.append((address, value))
            total_delegating += value

        sender_account = context.storage.icx.get_account(context, SENDER_ADDRESS, Intent.ALL)
        cached_accounts[SENDER_ADDRESS] = sender_account, 0

        # Put old delegations to cached_accounts
        for address, value in sender_account.delegations:
            account = context.storage.icx.get_account(context, address, Intent.DELEGATED)
            cached_accounts[address] = account, -value

        # Put new delegations to cached_accounts
        for i in range(10):
            value: int = i + 11
            address = Address.from_prefix_and_int(AddressPrefix.EOA, value)
            account = context.storage.icx.get_account(context, address, Intent.DELEGATED)
            cached_accounts[address] = account, value

        updated_accounts: List['Account'] = IISSEngine._put_delegation_to_state_db(
            context, SENDER_ADDRESS, new_delegations, cached_accounts)

        # sender_account(1) + old_delegated_accounts(10) + new_delegated_accounts(10)
        assert len(updated_accounts) == len(cached_accounts) == 21
        assert len(context.storage.icx.put_account.call_args_list) == len(cached_accounts)

        for i, address in enumerate(cached_accounts):
            call_args = context.storage.icx.put_account.call_args_list[i]
            account = call_args[0][1]
            assert isinstance(account, Account)
            assert address == account.address
            assert account == updated_accounts[i]

            if i == 0:
                assert account.address == SENDER_ADDRESS
                assert account.delegated_amount == 0
                assert account.delegations == new_delegations
                assert account.delegations_amount == total_delegating
            else:
                # Assume that all delegated accounts do not delegate any other accounts
                assert account.delegations_amount == 0

                if i <= 10:  # old delegations
                    assert account.delegated_amount == 0
                else:
                    assert account.delegated_amount == cached_accounts[address][1]

    def test_handle_set_delegation_with_21_accounts(self):
        context = Mock()
        context.tx.origin = SENDER_ADDRESS
        context.storage.icx.get_account = Mock(side_effect=get_account)
        total_delegating, params = create_delegations_param()

        class IISSEngineListenerImpl(IISSEngineListener):
            def on_set_stake(self, _context: 'IconScoreContext', account: 'Account'):
                assert False

            def on_set_delegation(self, _context: 'IconScoreContext', updated_accounts: List['Account']):
                assert len(updated_accounts) == 21

                for i, account in enumerate(updated_accounts):
                    assert isinstance(account, Account)
                    address = account.address
                    assert address == Address.from_prefix_and_int(AddressPrefix.EOA, i)

                    if i == 0:
                        # sender_account
                        assert account.delegated_amount == 0
                        assert len(account.delegations) == 10
                        assert account.delegation_part.delegations_amount == sum(range(11, 21))

                        for j, item in enumerate(account.delegations):
                            address: 'Address' = item[0]
                            value: int = item[1]

                            _id = j + 11
                            assert address == Address.from_prefix_and_int(AddressPrefix.EOA, _id)
                            assert value == _id
                    else:
                        assert account.delegations_amount == 0

                        if i <= 10:
                            assert account.delegated_amount == 0
                        else:
                            assert account.delegated_amount == i

        engine = IISSEngine()
        engine.add_listener(IISSEngineListenerImpl())
        engine.handle_set_delegation(context, params)

    def test_handle_set_delegation_with_1_account(self):
        context = Mock()
        context.tx.origin = SENDER_ADDRESS
        context.storage.icx.get_account = Mock(side_effect=get_account)

        params = {}
        new_delegations = [{
            "address": str(Address.from_prefix_and_int(AddressPrefix.EOA, 1)),
            "value": hex(100)
        }]
        params[ConstantKeys.DELEGATIONS] = new_delegations

        class IISSEngineListenerImpl(IISSEngineListener):
            def on_set_stake(self, _context: 'IconScoreContext', account: 'Account'):
                assert False

            def on_set_delegation(self, _context: 'IconScoreContext', updated_accounts: List['Account']):
                # sender_account(1) + updated_delegated_account(10)
                assert len(updated_accounts) == 11

                delegated_address = Address.from_prefix_and_int(AddressPrefix.EOA, 1)

                for i, account in enumerate(updated_accounts):
                    assert isinstance(account, Account)
                    address = account.address

                    if i == 0:
                        # sender_account
                        assert account.delegated_amount == 0
                        assert len(account.delegations) == 1
                        assert account.delegation_part.delegations_amount == 100

                        item = account.delegations[0]
                        assert item[0] == Address.from_prefix_and_int(AddressPrefix.EOA, 1)
                        assert item[1] == 100
                    else:
                        assert account.delegations_amount == 0

                        if address == delegated_address:
                            assert account.delegated_amount == 100
                        else:
                            assert account.delegated_amount == 0

        engine = IISSEngine()
        engine.add_listener(IISSEngineListenerImpl())
        engine.handle_set_delegation(context, params)

    def test_internal_handle_set_delegation(self):
        """Test case
        old_delegations: 1 ~ 10 delegated amount
        new_delegations: 101 ~ 110 delegated amount
        sender_account does not delegate to itself

        :return:
        """
        total_delegating, params = create_delegations_param()

        ret_total_delegating, ret_delegations = IISSEngine._convert_params_of_set_delegation(params)
        assert ret_total_delegating == total_delegating

        new_delegations = params[ConstantKeys.DELEGATIONS]
        for i in range(len(new_delegations)):
            item: Tuple['Address', int] = ret_delegations[i]
            address: 'Address' = item[0]
            value: int = item[1]

            assert str(address) == new_delegations[i]["address"]
            assert hex(value) == new_delegations[i]["value"]

        # IISSEngine._check_voting_power_is_enough()
        cached_accounts: Dict['Address', Tuple['Account', int]] = {}
        context = Mock()
        context.storage.icx.get_account = Mock(side_effect=get_account)
        IISSEngine._check_voting_power_is_enough(
            context, SENDER_ADDRESS, total_delegating, cached_accounts)

        assert len(cached_accounts) == 1
        assert cached_accounts[SENDER_ADDRESS][0] == create_sender_account(stake=10_000)
        assert cached_accounts[SENDER_ADDRESS][1] == 0  # delegated_amount

        sender_account: 'Account' = cached_accounts[SENDER_ADDRESS][0]

        # Get old delegations from delegating accounts
        IISSEngine._get_old_delegations_from_sender_account(context, SENDER_ADDRESS, cached_accounts)
        assert len(cached_accounts) == 11  # sender_account(1) + old delegated_accounts(10)

        for i, address in enumerate(cached_accounts):
            item: Tuple['Account', int] = cached_accounts[address]
            account = item[0]
            delegated_offset = item[1]

            assert address == account.address

            if i > 0:
                delegation: Tuple['Account', int] = sender_account.delegations[i - 1]
                assert address == delegation[0]
                assert delegated_offset == -delegation[1]

        IISSEngine._calc_delegations(context, ret_delegations, cached_accounts)
        # 0: sender_account, 1~10: old_accounts 11~20: new_accounts

        for i, address in enumerate(cached_accounts):
            account, delegated_offset = cached_accounts[address]
            assert account.address == address

            if i == 0:
                assert address == SENDER_ADDRESS
                assert delegated_offset == 0
            elif 1 <= i <= 10:
                assert delegated_offset == -i
            else:  # 11 <= i <= 20
                assert delegated_offset == i

        updated_accounts: List['Account'] = \
            IISSEngine._put_delegation_to_state_db(context, SENDER_ADDRESS, ret_delegations, cached_accounts)
        # sender_account(1) + old_delegated_accounts(10) + new_delegated_accounts(10)
        assert len(updated_accounts) == len(cached_accounts) == 21
        assert len(context.storage.icx.put_account.call_args_list) == len(cached_accounts)

        for i, address in enumerate(cached_accounts):
            call_args = context.storage.icx.put_account.call_args_list[i]
            account = call_args[0][1]
            assert isinstance(account, Account)
            assert address == account.address
            assert account == updated_accounts[i]

            if i == 0:
                assert account.address == SENDER_ADDRESS
                assert account.delegated_amount == 0
            elif 1 <= i <= 10:  # old delegations
                assert account.delegated_amount == 0
            else:
                assert account.delegated_amount == cached_accounts[address][1]


if __name__ == '__main__':
    unittest.main()
