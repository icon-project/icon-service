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


def test_get_prefix_EOA():
    addr = create_address()
    assert str(addr.prefix) == ICON_EOA_ADDRESS_PREFIX
    assert addr.prefix == AddressPrefix.EOA


def test_get_prefix_CONTRACT():
    addr = create_address(1)
    assert str(addr.prefix) == ICON_CONTRACT_ADDRESS_PREFIX
    assert addr.prefix == AddressPrefix.CONTRACT


def test_eq_EOA():
    addr1 = create_address(data=b'addr')
    addr2 = create_address(data=b'addr')
    assert addr1 == addr2


def test_eq_CONTRACT():
    addr1 = create_address(prefix=1, data=b'addr')
    addr2 = create_address(prefix=1, data=b'addr')
    assert addr1 == addr2


def test_ne_EOA():
    addr1 = create_address(data=b'addr1')
    addr2 = create_address(data=b'addr2')
    assert addr1 != addr2


def test_ne_CONTRACT():
    addr1 = create_address(prefix=1, data=b'addr1')
    addr2 = create_address(prefix=1, data=b'addr2')
    assert addr1 != addr2


def test_hash_EOA():
    addr1 = create_address(data=b'addr')
    addr2 = create_address(data=b'addr')
    assert addr1 == addr2
    assert hash(addr1) == hash(addr2)
    assert addr1 is not addr2

    table = {addr1: 100}
    assert table[addr1] == table[addr2]


def test_hash_CONTRACT():
    addr1 = create_address(prefix=1, data=b'addr')
    addr2 = create_address(prefix=1, data=b'addr')
    assert addr1 == addr2
    assert hash(addr1) == hash(addr2)
    assert addr1 is not addr2

    table = {addr1: 100}
    assert table[addr1] == table[addr2]


def test_address_from_to_bytes_EOA():
    addr1 = create_address()
    buf = addr1.to_bytes()
    addr2 = Address.from_bytes(buf)
    assert addr1 == addr2


def test_address_from_to_bytes_CONTRACT():
    addr1 = create_address(prefix=1)
    buf = addr1.to_bytes()
    addr2 = Address.from_bytes(buf)
    assert addr1 == addr2


def test_address_from_to_bytes_OTHER():
    addr1 = create_address()
    buf = addr1.to_bytes()
    prefix: int = 0
    prefix_buf: bytes = prefix.to_bytes(1, 'big')
    buf = prefix_buf + buf
    addr2 = Address.from_bytes(buf)
    assert addr1 == addr2


def test_address_from_to_string_EOA():
    addr1 = create_address()
    buf = str(addr1)
    addr2 = Address.from_string(buf)
    assert addr1 == addr2


def test_address_from_to_string_EOA2():
    addr1 = create_address()
    buf = bytes.hex(addr1.body)
    with pytest.raises(BaseException) as e:
        Address.from_string(buf)
    assert e.value.code == ExceptionCode.INVALID_PARAMETER
    assert e.value.message == 'Invalid address'


def test_address_from_to_string_CONTRACT():
    addr1 = create_address(prefix=1)
    buf = str(addr1)
    addr2 = Address.from_string(buf)
    assert addr1 == addr2


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


def test_split_icon_address():
    address = create_address()
    prefix, body = split_icon_address(str(address))
    assert prefix == str(address.prefix)
    assert body == bytes.hex(address.body)


def test_prefix_and_int():
    assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 0) == ZERO_SCORE_ADDRESS
    assert Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1) == GOVERNANCE_SCORE_ADDRESS
    assert str(Address.from_prefix_and_int(AddressPrefix.EOA, 10)) == "hx000000000000000000000000000000000000000a"
    assert str(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1024)) == \
           "cx0000000000000000000000000000000000000400"


def test_malformed_address():
    address: str = "hx123456"
    addr = MalformedAddress.from_string(address)
    assert str(addr) == address


def test_invalid_address():
    address: str = "hx123456"
    with pytest.raises(BaseException) as e:
        Address.from_string(address)
    assert e.value.code ==  ExceptionCode.INVALID_PARAMETER
    assert e.value.message == "Invalid address"


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
