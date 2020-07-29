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

from iconservice.base.address import ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from iconservice.base.exception import InvalidParamsException, ExceptionCode
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

    def test_delegation_part_for_delegation(self):
        src = DelegationPart()
        preps: list = []

        for _ in range(0, 10):
            prep: 'DelegationPart' = DelegationPart()
            prep.update_delegated_amount(10)
            preps.append((prep, 10))

        src.set_delegations(preps)

        self.assertEqual(10, len(src.delegations))

        for i in range(0, 10):
            prep, value = preps[i]
            self.assertEqual(10, prep.delegated_amount)

    def test_delegation_part_make_key(self):
        key = DelegationPart.make_key(create_address())
        self.assertEqual(ICON_EOA_ADDRESS_BYTES_SIZE + len(DelegationPart.PREFIX) + 1, len(key))

        key = DelegationPart.make_key(create_address(1))
        self.assertEqual(ICON_CONTRACT_ADDRESS_BYTES_SIZE + len(DelegationPart.PREFIX), len(key))

    def test_delegation_part_delegated_amount(self):
        delegated_amount = 10000
        part = DelegationPart(delegated_amount=delegated_amount)
        self.assertEqual(delegated_amount, part.delegated_amount)

    def test_delegation_part_delegations(self):
        count = 10
        amount = 10
        delegations = []
        for _ in range(count):
            delegations.append((create_address(), amount))

        part = DelegationPart(delegations=delegations)
        self.assertEqual(delegations, part.delegations)
        delegations_amount = amount * count
        self.assertEqual(delegations_amount, part.delegations_amount)

    def test_delegation_part_update_delegated_amount(self):
        offset = 100
        part = DelegationPart()

        self.assertFalse(part.is_dirty())
        part.update_delegated_amount(offset)
        self.assertTrue(part.is_dirty())

        self.assertEqual(offset, part.delegated_amount)

    def test_delegation_part_set_delegations(self):
        count = 10
        amount = 10
        delegations = []
        for _ in range(count):
            delegations.append((create_address(), amount))

        part = DelegationPart()

        self.assertFalse(part.is_dirty())
        part.set_delegations(delegations)
        self.assertTrue(part.is_dirty())

        self.assertEqual(delegations, part.delegations)

    def test_delegation_part_equal(self):
        part1 = DelegationPart()
        part2 = DelegationPart()
        self.assertEqual(part1, part2)

        offset = 100
        part1.update_delegated_amount(offset)

        part3 = DelegationPart(delegated_amount=offset)
        self.assertEqual(part1, part3)


if __name__ == '__main__':
    unittest.main()
