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
    @staticmethod
    def test_get_prefix_EOA():
        addr = create_address()
        assert str(addr.prefix) == ICON_EOA_ADDRESS_PREFIX
        assert addr.prefix == AddressPrefix.EOA

    @staticmethod
    def test_get_prefix_CONTRACT():
        addr = create_address(1)
        assert str(addr.prefix) == ICON_CONTRACT_ADDRESS_PREFIX
        assert addr.prefix == AddressPrefix.CONTRACT

    @pytest.mark.parametrize("prefix,data", [(0, b'addr'), (1, b'addr')])
    @staticmethod
    def test_eq(prefix, data):
        addr1 = create_address(prefix=prefix, data=data)
        addr2 = create_address(prefix=prefix, data=data)
        assert addr1 == addr2

    @pytest.mark.parametrize("prefix,data1,data2", [(0, b'addr1', b'addr2'), (1, b'addr1', b'addr2')])
    @staticmethod
    def test_ne_EOA(prefix, data1, data2):
        addr1 = create_address(prefix=prefix, data=data1)
        addr2 = create_address(prefix=prefix, data=data2)
        assert addr1 != addr2


    @pytest.mark.parametrize("prefix,data", [(0, b'addr'), (1, b'addr')])
    @staticmethod
    def test_hash(prefix, data):
        addr1 = create_address(prefix=prefix, data=data)
        addr2 = create_address(prefix=prefix, data=data)
        assert addr1 == addr2
        assert hash(addr1) == hash(addr2)
        assert addr1 is not addr2

        table = {addr1: 100}
        assert table[addr1] == table[addr2]

    @pytest.mark.parametrize("prefix", [0, 1])
    @staticmethod
    def test_address_from_to_bytes(prefix):
        addr1 = create_address(prefix)
        buf = addr1.to_bytes()
        addr2 = Address.from_bytes(buf)
        assert addr1 == addr2

    @staticmethod
    def test_address_from_to_bytes_OTHER():
        addr1 = create_address()
        buf = addr1.to_bytes()
        prefix: int = 0
        prefix_buf: bytes = prefix.to_bytes(1, 'big')
        buf = prefix_buf + buf
        addr2 = Address.from_bytes(buf)
        assert addr1 == addr2

    @staticmethod
    def test_address_from_to_string_EOA_valid_data():
        addr1 = create_address()
        buf = str(addr1)
        addr2 = Address.from_string(buf)
        assert addr1 == addr2

    @staticmethod
    def test_address_from_to_string_EOA2_invalid_data():
        addr1 = create_address()
        buf = bytes.hex(addr1.body)
        with pytest.raises(BaseException) as e:
            Address.from_string(buf)
        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        assert e.value.message == 'Invalid address'

    @staticmethod
    def test_address_from_to_string_CONTRACT():
        addr1 = create_address(prefix=1)
        buf = str(addr1)
        addr2 = Address.from_string(buf)
        assert addr1 == addr2

    @staticmethod
    def test_is_icon_address_valid():
        address: str = str(create_address())
        assert is_icon_address_valid(address)

        # Remove prefix 'hx'
        a = address[2:]
        assert is_icon_address_valid(a) is False

        # short address
        a = address[:-1]
        assert is_icon_address_valid(a) is False

        # wrong param prefix
        assert is_icon_address_valid(1234) is False

        # wrong hexadecimal format
        assert is_icon_address_valid("0x00c3f694d84074f9145cd0bfa497290ce2d8052f") is False

    @staticmethod
    def test_split_icon_address():
        address = create_address()
        prefix, body = split_icon_address(str(address))
        assert prefix == str(address.prefix)
        assert body == bytes.hex(address.body)

    @staticmethod
    def test_prefix_and_int():
        assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 0) == ZERO_SCORE_ADDRESS
        assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1) == GOVERNANCE_SCORE_ADDRESS
        assert str(Address.from_prefix_and_int(AddressPrefix.EOA, 10)) == "hx000000000000000000000000000000000000000a"
        assert str(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1024)) == \
               "cx0000000000000000000000000000000000000400"

    @staticmethod
    def test_malformed_address():
        address: str = "hx123456"
        addr = MalformedAddress.from_string(address)
        assert str(addr) == address

    @staticmethod
    def test_invalid_address():
        address: str = "hx123456"
        with pytest.raises(BaseException) as e:
            Address.from_string(address)
        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        assert e.value.message == "Invalid address"

    @staticmethod
    def test_from_bytes_including_prefix():
        address_prefixes = [AddressPrefix.EOA, AddressPrefix.CONTRACT]

        value: int = random.randint(0, 0xffffffff)
        input_data: bytes = value.to_bytes(4, 'big')
        data: bytes = hashlib.sha3_256(input_data).digest()

        for prefix in address_prefixes:
            body: bytes = data[-20:]
            assert 20 == len(body)

            address_bytes: bytes = prefix.to_bytes(1, 'big') + body
            address = Address.from_bytes_including_prefix(address_bytes)

            assert prefix == address.prefix
            assert body == address.body

        for prefix in address_prefixes:
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

    @staticmethod
    def test_to_bytes_including_prefix():
        value: int = random.randint(0, 0xffffffff)
        input_data: bytes = value.to_bytes(4, 'big')
        data: bytes = hashlib.sha3_256(input_data).digest()
        body: bytes = data[-20:]

        for prefix in [AddressPrefix.EOA, AddressPrefix.CONTRACT]:
            address = Address(prefix, body)
            address_bytes: bytes = address.to_bytes_including_prefix()

            expected_bytes: bytes = prefix.to_bytes(1, 'big') + body
            assert isinstance(address_bytes, bytes)
            assert 21 == len(address_bytes)
            assert expected_bytes == address_bytes


class TestMalformedAddress:
    @staticmethod
    def test_from_string():
        address = MalformedAddress.from_string('')
        assert address.prefix == AddressPrefix.EOA
        assert address.body == b''
        assert str(address) == 'hx'

        short_address_without_hx = MalformedAddress.from_string('123124124125')
        assert short_address_without_hx.prefix == AddressPrefix.EOA
        assert str(short_address_without_hx) == 'hx123124124125'
        assert short_address_without_hx.body == bytes.fromhex('123124124125')

        text = 'bf85fac2d1b507a2db9ce9526e6d91476f16a2d269f51636f9c4b2d512017faf'
        long_address_without_hx = MalformedAddress.from_string(text)
        assert long_address_without_hx.prefix == AddressPrefix.EOA
        assert str(long_address_without_hx) == f'hx{text}'
        assert long_address_without_hx.body == bytes.fromhex(text)

        long_address = MalformedAddress.from_string(f'hx{text}')
        assert long_address == long_address_without_hx

        text = 'hxa23651905d221dd36b'
        short_address = MalformedAddress.from_string(text)
        assert short_address.prefix == AddressPrefix.EOA
        assert str(short_address) == text
        assert short_address.body == bytes.fromhex('a23651905d221dd36b')
