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
from iconservice.database.batch import TransactionBatch, IconScoreBatch
from iconservice.utils import int_to_bytes
from tests import create_tx_hash, create_address


class TestTransactionBatch(unittest.TestCase):
    def setUp(self):
        self.tx_hash = create_tx_hash(b'tx_hash')
        self.tx_batch = TransactionBatch(self.tx_hash)

        self.score_address = create_address(AddressPrefix.CONTRACT, b'score')
        self.eoa_address = create_address(AddressPrefix.EOA, b'eoa')
        self.tx_batch.put(self.score_address, self.eoa_address, value=int_to_bytes(1))

    def test_get_item(self):
        icon_score_batch = self.tx_batch[self.score_address]
        self.assertEqual(int_to_bytes(1), icon_score_batch[self.eoa_address])

    def test_len(self):
        i = 0
        for key in self.tx_batch:
            self.assertTrue(isinstance(key, Address))
            self.assertTrue(isinstance(self.tx_batch[key], IconScoreBatch))
            i += 1

        self.assertTrue(i > 0)
        self.assertEqual(i, len(self.tx_batch))

    def test_put(self):
        address = create_address(AddressPrefix.EOA, b'addr1')
        value = int_to_bytes(15)
        self.tx_batch.put(self.score_address, address.body, value)
        self.assertEqual(1, len(self.tx_batch))
        self.assertEqual(value, self.tx_batch[self.score_address][address.body])

        score_address = create_address(AddressPrefix.CONTRACT, b'score1')
        value = int_to_bytes(7)
        self.tx_batch.put(score_address, address.body, value)
        self.assertEqual(2, len(self.tx_batch))
        self.assertEqual(value, self.tx_batch[score_address][address.body])
