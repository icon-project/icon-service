#!/usr/bin/env python
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
from unittest import TestCase

from iconservice.base.address import AddressPrefix
from iconservice.fee.deposit import Deposit
from iconservice.utils import to_camel_case
from tests import create_tx_hash, create_address


class TestDeposit(TestCase):

    def test_to_bytes_from_bytes(self):
        """
        - Checks if Deposit object in bytes is converted into Deposit object correctly.
        - Checks if Deposit object is converted into Deposit object in bytes correctly.
        """
        deposit = Deposit()
        deposit.id = create_tx_hash()
        deposit.score_address = create_address(AddressPrefix.CONTRACT)
        deposit.sender = create_address(AddressPrefix.EOA)
        deposit.deposit_amount = 10000
        deposit.deposit_used = 10000
        deposit.created = 10
        deposit.expires = 1000000
        deposit.virtual_step_issued = 100000000000
        deposit.virtual_step_used = 200000000000
        deposit.prev_id = create_tx_hash()
        deposit.next_id = create_tx_hash()

        deposit_in_bytes = deposit.to_bytes()
        self.assertIsInstance(deposit_in_bytes, bytes)
        deposit2 = Deposit.from_bytes(deposit_in_bytes)
        self.assertIsInstance(deposit2, Deposit)
        self.assertEqual(deposit, deposit2)

    def test_to_bytes_from_bytes_with_none_type(self):
        deposit = Deposit()
        deposit.score_address = create_address(AddressPrefix.CONTRACT)
        deposit.sender = create_address(AddressPrefix.EOA)

        deposit_in_bytes = deposit.to_bytes()
        self.assertIsInstance(deposit_in_bytes, bytes)
        deposit2 = Deposit.from_bytes(deposit_in_bytes)
        self.assertIsInstance(deposit2, Deposit)
        self.assertEqual(deposit, deposit2)

    def test_to_dict(self):
        """
        - Checks if Deposit.to_dict method makes the object to dict type correctly.
        - Checks if Deposit.to_dict method makes the object to dict type as casing like camel case correctly.
        """
        deposit = Deposit()
        deposit.id = create_tx_hash()
        deposit.score_address = create_address(AddressPrefix.CONTRACT)
        deposit.sender = create_address(AddressPrefix.EOA)
        deposit.deposit_amount = 10000
        deposit.deposit_used = 10000
        deposit.created = 10
        deposit.expires = 1000000
        deposit.virtual_step_issued = 100000000000
        deposit.virtual_step_used = 200000000000
        deposit.prev_id = create_tx_hash()
        deposit.next_id = create_tx_hash()

        deposit_in_dict = deposit.to_dict()
        self.assertIsInstance(deposit_in_dict, dict)

        deposit_in_dict_to_camel_case = deposit.to_dict(to_camel_case)
        self.assertIsInstance(deposit_in_dict_to_camel_case, dict)

        attributes = dir(deposit)[-16:]
        cnt_attr = 0
        for attr in attributes:
            if attr in ('to_bytes', 'to_dict', 'from_bytes', 'remaining_deposit', 'remaining_virtual_step'):
                continue
            self.assertIn(attr, deposit_in_dict)
            self.assertIn(to_camel_case(attr), deposit_in_dict_to_camel_case)
            cnt_attr += 1
        self.assertEqual(11, cnt_attr)
