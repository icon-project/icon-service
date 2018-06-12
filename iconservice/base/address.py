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

"""functions and classes to handle address
"""

import hashlib
from enum import IntEnum
from ..utils import is_lowercase_hex_string


ICON_EOA_ADDRESS_PREFIX = 'hx'
ICON_CONTRACT_ADDRESS_PREFIX = 'cx'


def is_icon_address_valid(address: str) -> bool:
    """Check whether address is in icon address format or not

    :param address: (str) address string including prefix
    :return: (bool)
    """
    try:
        if isinstance(address, str) and len(address) == 42:
            prefix, body = split_icon_address(address)
            if prefix == ICON_EOA_ADDRESS_PREFIX or \
                    prefix == ICON_CONTRACT_ADDRESS_PREFIX:
                return is_lowercase_hex_string(body)
    finally:
        pass

    return False


def split_icon_address(address: str) -> (str, str):
    """Split icon address into 2-char prefix and 40-char address body

    :param address: 42-char address string
    :return: prefix, body
    """
    return address[:2], address[2:]


class AddressPrefix(IntEnum):
    """Address prefix class
    """
    # Externally Owned Account
    EOA = 0
    CONTRACT = 1

    def __str__(self) -> str:
        if self == AddressPrefix.EOA:
            return ICON_EOA_ADDRESS_PREFIX
        if self == AddressPrefix.CONTRACT:
            return ICON_CONTRACT_ADDRESS_PREFIX

    @staticmethod
    def from_string(prefix: str):
        """Returns address prefix enumerator

        :param prefix: 2-byte address prefix (hx or cx)
        :return: (AddressPrefix) address prefix enumerator
        """
        if prefix == ICON_EOA_ADDRESS_PREFIX:
            return AddressPrefix.EOA
        if prefix == ICON_CONTRACT_ADDRESS_PREFIX:
            return AddressPrefix.CONTRACT

        raise ValueError('Invalid address prefix')


class Address(object):
    """Address class
    """

    def __init__(self,
                 address_prefix: AddressPrefix,
                 address_body: bytes) -> None:
        """Constructor

        :param address_prefix: address prefix enumerator
        :param address_body: 20-byte address body
        """
        if not isinstance(address_prefix, AddressPrefix):
            raise TypeError('Invalid address prefix type')
        if not isinstance(address_body, bytes):
            raise TypeError('Invalid address body type')
        if len(address_body) != 20:
            raise ValueError('Length of address body should be 20 in bytes')

        self.__prefix = address_prefix
        self.__body = address_body

    @property
    def prefix(self) -> AddressPrefix:
        """Returns address prefix part

        :return: AddressPrefix.EOA(0) or AddressPrefix.CONTRACT(1)
        """
        return self.__prefix

    @property
    def body(self) -> bytes:
        """Returns 20-byte address body part

        :return: 20 byte data standing for address
        """
        return self.__body

    def __eq__(self, other) -> bool:
        """operator == overriding

        :return: bool
        """
        return \
            isinstance(other, Address) \
            and self.__prefix == other.prefix \
            and self.__body == other.body

    def __ne__(self, other) -> bool:
        """operator != overriding

        :return: (bool)
        """
        return not self.__eq__(other)

    def __str__(self) -> str:
        """operator str() overriding

        returns prefix(2) + 40-char hexadecimal address

        :return: (str) 42-char address
        """
        return f'{str(self.prefix)}{self.body.hex()}'

    def __hash__(self) -> int:
        """Returns a hash value for this object

        :return: hash value
        """
        return hash(self.__prefix.to_bytes(1, 'big') + self.__body)

    @property
    def is_contract(self) -> bool:
        """Is this a contract address?

        :return: True(contract) False(Not contract)
        """
        return self.prefix == AddressPrefix.CONTRACT

    @staticmethod
    def from_string(address: str):
        """Create Address object from 42-char address

        :return: (Address)
        """

        if not is_icon_address_valid(address):
            raise ValueError('Invalid address')

        prefix, body = split_icon_address(address)

        address_prefix = AddressPrefix.from_string(prefix)
        address_body = bytes.fromhex(body)

        return Address(address_prefix, address_body)

    @staticmethod
    def from_data(prefix: AddressPrefix, data: bytes):
        return create_address(prefix, data)


def create_address(prefix: AddressPrefix, data: bytes):
    hash_value = hashlib.sha3_256(data).digest()
    return Address(prefix, hash_value[-20:])


ICX_ENGINE_ADDRESS = create_address(AddressPrefix.CONTRACT, b'icon_dex')
