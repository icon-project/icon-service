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


import pytest

from iconservice.base.address import ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.base.exception import InvalidParamsException, OutOfBalanceException
from iconservice.icon_constant import Revision, DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER
from iconservice.icx.base_part import BasePartState
from iconservice.icx.coin_part import CoinPartType, CoinPartFlag, CoinPart, CoinPartVersion
from iconservice.utils import set_flag
from iconservice.utils.msgpack_for_db import MsgPackForDB
from tests import create_address


class TestAccountType:
    def test_account_type(self):
        assert 0 == CoinPartType.GENERAL
        assert 1 == CoinPartType.GENESIS
        assert 2 == CoinPartType.TREASURY
        assert 'GENERAL' == str(CoinPartType.GENERAL)
        assert 'GENESIS' == str(CoinPartType.GENESIS)
        assert 'TREASURY' == str(CoinPartType.TREASURY)

    def test_from_int(self):
        assert CoinPartType(0) == CoinPartType.GENERAL
        assert CoinPartType(1) == CoinPartType.GENESIS
        assert CoinPartType(2) == CoinPartType.TREASURY
        pytest.raises(ValueError, CoinPartType, 3)


class TestCoinPart:
    def test_coin_part_revision_3(self):
        part1 = CoinPart()
        assert part1 is not None
        assert CoinPartFlag.NONE is part1.flags
        assert part1.balance == 0

        part1.deposit(100)
        assert 100 == part1.balance

        part1.withdraw(100)
        assert 0 == part1.balance

        # wrong value
        with pytest.raises(InvalidParamsException):
            part1.deposit(-10)

        # 0 transfer is possible
        old = part1.balance
        part1.deposit(0)
        assert old == part1.balance

        with pytest.raises(InvalidParamsException):
            part1.withdraw(-11234)

        with pytest.raises(OutOfBalanceException):
            part1.withdraw(1)

        old = part1.balance
        part1.withdraw(0)
        assert old == part1.balance

    @pytest.mark.parametrize("revision", [Revision(3), Revision(4)])
    def test_coin_part_from_bytes_to_bytes_revision_3_to_4(self, revision):
        # Todo: No need to tests after revision 4?
        part1 = CoinPart()
        data = part1.to_bytes(revision.value)
        assert isinstance(data, bytes) is True
        assert len(data) == 36

        part2 = CoinPart.from_bytes(data)
        assert part2.type == CoinPartType.GENERAL
        assert part2.balance == 0

        part1.type = CoinPartType.GENESIS
        part1.deposit(1024)

        part3 = CoinPart.from_bytes(part1.to_bytes(revision.value))
        assert part3.type == CoinPartType.GENESIS
        assert part3.balance == 1024

    def test_coin_part_from_bytes_to_bytes_old_db_load_revision_4(self):
        part1 = CoinPart()

        balance = 1024
        part1.type = CoinPartType.GENERAL
        part1.deposit(balance)

        part2 = CoinPart.from_bytes(part1.to_bytes(Revision.THREE.value))
        assert part2 == part1

        data: bytes = part1.to_bytes(Revision.FOUR.value)
        part3 = CoinPart.from_bytes(data)
        assert part3 == part1

    def test_coin_part_flag(self):
        part1 = CoinPart()
        assert part1.states == BasePartState.NONE

        part1._flags = set_flag(part1.flags, CoinPartFlag.HAS_UNSTAKE, True)
        assert CoinPartFlag.HAS_UNSTAKE in part1.flags

        part1._flags = set_flag(part1.flags, CoinPartFlag.HAS_UNSTAKE, False)
        assert CoinPartFlag.NONE == part1.flags
        assert CoinPartFlag.HAS_UNSTAKE not in part1.flags

    def test_coin_part_make_key(self):
        key = CoinPart.make_key(create_address())
        assert ICON_EOA_ADDRESS_BYTES_SIZE == len(key)

        key = CoinPart.make_key(create_address(1))
        assert ICON_CONTRACT_ADDRESS_BYTES_SIZE == len(key)

    def test_coin_part_type_property(self):
        part = CoinPart()
        assert CoinPartType.GENERAL == part.type

        for coin_part_type in CoinPartType:
            part = CoinPart(coin_part_type=coin_part_type)
            assert coin_part_type == part.type

        for coin_part_type in CoinPartType:
            part = CoinPart()
            part.type = coin_part_type
            assert coin_part_type == part.type

        with pytest.raises(ValueError) as e:
            part.type = len(CoinPartType) + 1

        assert "Invalid CoinPartType" == e.value.args[0]

    def test_coin_part_balance(self):
        balance = 10000
        part = CoinPart(balance=balance)
        assert balance == part.balance

    def test_coin_part_flags(self):
        part = CoinPart(flags=CoinPartFlag.HAS_UNSTAKE)
        assert CoinPartFlag.HAS_UNSTAKE == part.flags

    def test_coin_part_deposit(self):
        balance = 100
        part = CoinPart()

        assert part.is_dirty() is False
        part.deposit(balance)
        assert part.is_dirty() is True

        assert balance == part.balance

    def test_coin_part_withdraw(self):
        balance = 100
        part = CoinPart()

        assert part.is_dirty() is False
        part.deposit(balance)
        part.withdraw(balance)
        assert part.is_dirty() is True
        assert 0 == part.balance

    def test_coin_part_equal(self):
        part1 = CoinPart()
        part2 = CoinPart()
        assert part1 == part2

        balance = 100
        part1.deposit(balance)
        part3 = CoinPart(balance=balance)
        assert part1 == part3

    @pytest.mark.parametrize("revision", [i for i in range(Revision.IISS.value)])
    def test_coin_part_to_bytes_before_rev_iiss(self, revision):
        coin_type = CoinPartType.GENERAL
        coin_flag = CoinPartFlag.NONE
        value = 5

        coin_part = CoinPart(coin_type, coin_flag, value)
        actual_bytes = coin_part.to_bytes(revision)
        expected_bytes = CoinPart._STRUCT_FORMAT.pack(CoinPartVersion.STRUCT,
                                                      CoinPartType.GENERAL.value,
                                                      CoinPartFlag.NONE.value,
                                                      value.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))

        assert actual_bytes == expected_bytes

    @pytest.mark.parametrize(
        "revision",
        [i for i in range(Revision.IISS.value, Revision.FIX_COIN_PART_BYTES_ENCODING.value)]
    )
    def test_first_coin_part_to_bytes_from_rev_iiss_to_rev_9(self, revision):
        is_first = True
        coin_type = CoinPartType.GENERAL
        coin_flag = CoinPartFlag.NONE
        value = 5

        coin_part = CoinPart(coin_type, coin_flag, value, is_first)
        actual_bytes = coin_part.to_bytes(revision)

        # 94 means list in msgpack
        # def _pack_array_header(self, n):
        #      if n <= 0x0F:
        #      return self._buffer.write(struct.pack("B", 0x90 + n))
        expected_bytes = (
            b'\x94' +
            MsgPackForDB.dumps(CoinPartVersion.MSG_PACK) +
            MsgPackForDB.dumps(CoinPartType.GENERAL) +
            coin_flag.value.to_bytes(1, DATA_BYTE_ORDER) +
            value.to_bytes(1, DATA_BYTE_ORDER)
        )

        assert actual_bytes == expected_bytes

    @pytest.mark.parametrize(
        "revision",
        [i for i in range(Revision.IISS.value, Revision.FIX_COIN_PART_BYTES_ENCODING.value)]
    )
    def test_coin_part_to_bytes_from_rev_iiss_to_rev_9(self, revision):
        is_first = False
        coin_type = CoinPartType.GENERAL
        coin_flag = CoinPartFlag.NONE
        value = 5

        coin_part = CoinPart(coin_type, coin_flag, value, is_first)
        actual_bytes = coin_part.to_bytes(revision)

        expected_bytes = b'\x94' + \
                         MsgPackForDB.dumps(CoinPartVersion.MSG_PACK) + \
                         coin_type.value.to_bytes(1, DATA_BYTE_ORDER) + \
                         coin_flag.value.to_bytes(1, DATA_BYTE_ORDER) + \
                         value.to_bytes(1, DATA_BYTE_ORDER)

        assert actual_bytes == expected_bytes

    def test_coin_part_to_bytes_from_after_rev_9(self):
        revision = Revision.FIX_COIN_PART_BYTES_ENCODING.value
        coin_type = CoinPartType.GENERAL
        coin_flag = CoinPartFlag.NONE
        value = 5

        coin_part = CoinPart(coin_type, coin_flag, value)
        actual_bytes = coin_part.to_bytes(revision)

        expected_bytes = b'\x94' + \
                         CoinPartVersion.MSG_PACK.value.to_bytes(1, DATA_BYTE_ORDER) + \
                         coin_type.value.to_bytes(1, DATA_BYTE_ORDER) + \
                         coin_flag.value.to_bytes(1, DATA_BYTE_ORDER) + \
                         value.to_bytes(1, DATA_BYTE_ORDER)

        assert actual_bytes == expected_bytes
