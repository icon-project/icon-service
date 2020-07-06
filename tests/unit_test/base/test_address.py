# -*- coding: utf-8 -*-

# Copyright 2020 ICON Foundation
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

import hashlib
import random

import pytest

from iconservice.base.address import Address, AddressPrefix, ICON_EOA_ADDRESS_PREFIX, ICON_CONTRACT_ADDRESS_PREFIX, \
    ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, is_icon_address_valid, split_icon_address, MalformedAddress
from iconservice.base.exception import ExceptionCode
from tests import create_address


class TestAddress:
    @pytest.mark.parametrize("prefix,expected_prefix,expected_prefix_constant",
                             [(0, AddressPrefix.EOA, ICON_EOA_ADDRESS_PREFIX),
                              (1, AddressPrefix.CONTRACT, ICON_CONTRACT_ADDRESS_PREFIX)])
    def test_get_prefix(self, prefix, expected_prefix, expected_prefix_constant):
        addr = create_address(prefix=prefix)
        assert str(addr.prefix) == expected_prefix_constant
        assert addr.prefix == expected_prefix

    @pytest.mark.parametrize("prefix,data1,data2", [(0, b'addr1', b'addr2'), (1, b'addr1', b'addr2')])
    def test_equality(self, prefix, data1, data2):
        addr1 = create_address(prefix=prefix, data=data1)
        addr2 = create_address(prefix=prefix, data=data1)
        addr3 = create_address(prefix=prefix, data=data2)
        assert addr1 == addr2
        assert addr1 != addr3

    @pytest.mark.parametrize("prefix,data", [(0, b'addr'), (1, b'addr')])
    def test_hash(self, prefix, data):
        addr1 = create_address(prefix=prefix, data=data)
        addr2 = create_address(prefix=prefix, data=data)
        assert addr1 == addr2
        assert hash(addr1) == hash(addr2)
        assert addr1 is not addr2

        table = {addr1: 100}
        assert table[addr1] == table[addr2]

    @pytest.mark.parametrize("prefix", [0, 1])
    def test_address_from_to_bytes(self, prefix):
        addr1 = create_address(prefix)
        buf = addr1.to_bytes()
        addr2 = Address.from_bytes(buf)
        assert addr1 == addr2

    def test_address_from_to_bytes_eoa_20length_eq_21length_from_bytes(self):
        addr1 = create_address()
        buf = addr1.to_bytes()
        prefix: int = 0
        prefix_buf: bytes = prefix.to_bytes(1, 'big')
        buf = prefix_buf + buf
        addr2 = Address.from_bytes(buf)
        assert addr1 == addr2

    @pytest.mark.parametrize("prefix", [0, 1])
    def test_address_from_to_string(self, prefix):
        addr1 = create_address(prefix=prefix)
        buf = str(addr1)
        addr2 = Address.from_string(buf)
        assert addr1 == addr2

    @pytest.mark.parametrize("address", ["hx123456", bytes.hex(GOVERNANCE_SCORE_ADDRESS.body)])
    def test_from_string_invalid(self, address):
        with pytest.raises(BaseException) as e:
            Address.from_string(address)
        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        assert e.value.message == "Invalid address"

    def test_is_icon_address_valid_valid_case(self):
        address: str = str(create_address())
        assert is_icon_address_valid(address)

    @pytest.mark.parametrize("address_string", [f"{'1234'*10}", "12", 1234, f"0x{'1234'*10}"])
    def test_is_icon_address_valid_invalid_cases(self, address_string):
        """without prefix, shorten data, wrong prefix data"""
        assert is_icon_address_valid(address_string) is False

    def test_split_icon_address(self):
        address = create_address()
        prefix, body = split_icon_address(str(address))
        assert prefix == str(address.prefix)
        assert body == bytes.hex(address.body)

    def test_prefix_and_int(self):
        assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 0) == ZERO_SCORE_ADDRESS
        assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1) == GOVERNANCE_SCORE_ADDRESS
        assert str(Address.from_prefix_and_int(AddressPrefix.EOA, 10)) == "hx000000000000000000000000000000000000000a"
        assert str(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1024)) == \
               "cx0000000000000000000000000000000000000400"

    @pytest.mark.parametrize("prefix", [prefix for prefix in AddressPrefix])
    def test_from_bytes_including_prefix_valid(self, prefix):
        value: int = random.randint(0, 0xffffffff)
        input_data: bytes = value.to_bytes(4, 'big')
        data: bytes = hashlib.sha3_256(input_data).digest()

        body: bytes = data[-20:]
        assert 20 == len(body)

        address_bytes: bytes = prefix.to_bytes(1, 'big') + body
        address = Address.from_bytes_including_prefix(address_bytes)

        assert prefix == address.prefix
        assert body == address.body

    @pytest.mark.parametrize("prefix", [prefix for prefix in AddressPrefix])
    def test_from_bytes_including_prefix_invalid(self, prefix):
        value: int = random.randint(0, 0xffffffff)
        input_data: bytes = value.to_bytes(4, 'big')
        data: bytes = hashlib.sha3_256(input_data).digest()

        size = random.randint(1, 32)
        if size == 20:
            size += 1

        body: bytes = data[-size:]
        assert size == len(body)

        address_bytes: bytes = prefix.to_bytes(1, 'big') + body
        address = Address.from_bytes_including_prefix(address_bytes)
        assert address is None

        address = Address.from_bytes_including_prefix(body)
        assert address is None

    @pytest.mark.parametrize("prefix", [prefix for prefix in AddressPrefix])
    def test_to_bytes_including_prefix(self, prefix):
        value: int = random.randint(0, 0xffffffff)
        input_data: bytes = value.to_bytes(4, 'big')
        data: bytes = hashlib.sha3_256(input_data).digest()
        body: bytes = data[-20:]

        address = Address(prefix, body)
        address_bytes: bytes = address.to_bytes_including_prefix()

        expected_bytes: bytes = prefix.to_bytes(1, 'big') + body
        assert isinstance(address_bytes, bytes)
        assert 21 == len(address_bytes)
        assert expected_bytes == address_bytes


class TestMalformedAddress:
    @pytest.mark.parametrize("address_string", ['', '123124124125',
                                                'bf85fac2d1b507a2db9ce9526e6d91476f16a2d269f51636f9c4b2d512017faf'])
    def test_from_string_without_prefix(self, address_string):
        address = MalformedAddress.from_string(address_string)
        assert address.prefix == AddressPrefix.EOA
        assert address.body == bytes.fromhex(address_string)
        assert str(address) == f'hx{address_string}'

    def test_from_string_with_prefix(self):
        text = 'hxa23651905d221dd36b'
        short_address = MalformedAddress.from_string(text)
        assert short_address.prefix == AddressPrefix.EOA
        assert str(short_address) == text
        assert short_address.body == bytes.fromhex('a23651905d221dd36b')
