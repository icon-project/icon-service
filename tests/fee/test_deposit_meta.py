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

from iconservice.fee.deposit_meta import DepositMeta
from tests import create_tx_hash


class TestFee(TestCase):

    def test_deposit_meta_from_bytes_to_bytes(self):
        deposit_meta = DepositMeta()
        deposit_meta.head_id = create_tx_hash()
        deposit_meta.tail_id = create_tx_hash()
        deposit_meta.available_head_id_of_deposit = create_tx_hash()
        deposit_meta.available_head_id_of_virtual_step = create_tx_hash()
        deposit_meta.expires_of_deposit = 1
        deposit_meta.expires_of_virtual_step = 200
        deposit_meta.version = 3

        deposit_meta_in_bytes = deposit_meta.to_bytes()
        self.assertIsInstance(deposit_meta_in_bytes, bytes)

        deposit_meta_2 = DepositMeta.from_bytes(deposit_meta_in_bytes)
        self.assertIsInstance(deposit_meta_2, DepositMeta)
        self.assertEqual(deposit_meta, deposit_meta_2)

    def test_deposit_meta_to_bytes_from_bytes_with_none_type(self):
        deposit_meta = DepositMeta()
        deposit_meta_in_bytes = deposit_meta.to_bytes()
        self.assertIsInstance(deposit_meta_in_bytes, bytes)

        deposit_meta_2 = DepositMeta.from_bytes(deposit_meta_in_bytes)
        self.assertIsInstance(deposit_meta_2, DepositMeta)
        self.assertEqual(deposit_meta, deposit_meta_2)

