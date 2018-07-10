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

import unittest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.address import is_icon_address_valid
from iconservice.base.address import split_icon_address
from iconservice.logger import Logger


class TestAddress(unittest.TestCase):
    def test_get_prefix(self):
        text = 'hx1234567890123456789012345678901234567890'
        a = Address.from_string(text)
        self.assertTrue(a.prefix == AddressPrefix.EOA)

    def test_eq(self):
        text = 'hx1234567890123456789012345678901234567890'

        a = Address.from_string(text)
        b = Address.from_string(text)
        self.assertTrue(a == b)

    def test_ne(self):
        hex_a = 'hx1234567890123456789012345678901234abcdef'
        hex_b = 'hx1234567890123456789012345678901234abcde0'

        a = Address.from_string(hex_a)
        b = Address.from_string(hex_a)
        self.assertFalse(a != b)

        b = Address.from_string(hex_b)
        self.assertTrue(a != b)

    def test_is_icon_address_valid(self):
        address = 'hx00c3f694d84074f9145cd0bfa497290ce2d8052f'
        self.assertTrue(is_icon_address_valid(address))

        # Remove prefix 'hx'
        a = address[2:]
        self.assertFalse(is_icon_address_valid(a))

        # short address
        a = address[:-1]
        self.assertFalse(is_icon_address_valid(a))

        # wrong param prefix
        self.assertFalse(is_icon_address_valid(1234))

        # wrong hexadecimal format
        self.assertFalse(is_icon_address_valid(
            'hxz0c3f694d84074f9145cd0bfa497290ce2d8052f'))

    def test_split_icon_address(self):
        address = 'hx00c3f694d84074f9145cd0bfa497290ce2d8052f'
        prefix, body = split_icon_address(address)
        self.assertEqual(prefix, 'hx')
        self.assertEqual(body, '00c3f694d84074f9145cd0bfa497290ce2d8052f')

    def test_create_address_object(self):
        address = 'hx00c3f694d84074f9145cd0bfa497290ce2d8052f'
        _, body = split_icon_address(address)
        a = Address.from_string(address)
        self.assertEqual(a.prefix, AddressPrefix.EOA)
        self.assertEqual(a.body, bytes.fromhex(body))

        address = 'cx4ad7f694d84074f9145cd0bfa497290ce2d8052f'
        _, body = split_icon_address(address)
        a = Address.from_string(address)
        self.assertEqual(a.prefix, AddressPrefix.CONTRACT)
        self.assertEqual(a.body, bytes.fromhex(body))

    def test_hash(self):
        a1 = Address.from_string('hx00c3f694d84074f9145cd0bfa497290ce2d8052f')
        a2 = Address.from_string('hx00c3f694d84074f9145cd0bfa497290ce2d8052f')
        self.assertEqual(a1, a2)
        self.assertEqual(hash(a1), hash(a2))
        self.assertFalse(a1 is a2)

        table = {}
        table[a1] = 100
        self.assertEqual(table[a1], table[a2])


if __name__ == '__main__':
    unittest.main()
