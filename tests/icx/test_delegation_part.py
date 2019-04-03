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


import unittest

from iconservice import Address
from iconservice.icx.delegation_part import DelegationPart
from tests import create_address


class TestDelegationPart(unittest.TestCase):

    def test_delegation_part_from_bytes_to_bytes(self):
        account = DelegationPart()
        data = account.to_bytes()
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(4, len(data))

        account2 = DelegationPart.from_bytes(data)
        self.assertEqual(account.delegated_amount, account2.delegated_amount)
        self.assertEqual(account.delegations, account2.delegations)

    def test_account_for_delegation(self):
        accounts = []
        src_address: 'Address' = create_address()
        src = DelegationPart()

        for _ in range(0, 10):
            to_address: 'Address' = create_address()
            to: 'DelegationPart' = DelegationPart()
            accounts.append((to_address, to))
            src.delegate(to_address, to, 10)

        self.assertEqual(10, len(src.delegations))

        for i in range(0, 10):
            address, account = accounts[i]
            self.assertEqual(10, account.delegated_amount)

        for i in range(0, 10):
            address, account = accounts[i]
            src.delegate(address, account, 0)

        self.assertEqual(0, len(src.delegations))


if __name__ == '__main__':
    unittest.main()
