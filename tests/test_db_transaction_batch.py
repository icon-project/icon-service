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

from iconservice.base.address import Address
from iconservice.database.icon_score_batch import IconScoreBatch
from iconservice.database.transaction_batch import TransactionBatch


class TestTransactionBatch(unittest.TestCase):
    def setUp(self):
        self.tx_hash = '1c1efbdac604865ec9629f314e2fea57a3ee253283c8f0e5c1549a6a6c7a7775'
        self.tx_batch = TransactionBatch(self.tx_hash)

        score_address = Address.from_string(f'cx{"0" * 40}')
        eoa_address = Address.from_string(f'hx{"1" * 40}')
        self.tx_batch.put(score_address, eoa_address, 1)

    def test_get_item(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        eoa_address = Address.from_string(f'hx{"1" * 40}')
        icon_score_batch = self.tx_batch[score_address]
        self.assertEqual(1, icon_score_batch[eoa_address])

    def test_len(self):
        i = 0
        for key in self.tx_batch:
            self.assertTrue(isinstance(key, Address))
            self.assertTrue(isinstance(self.tx_batch[key], IconScoreBatch))
            i += 1

        self.assertTrue(i > 0)
        self.assertEqual(i, len(self.tx_batch))

    def test_put(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"f" * 40}')
        value = 15
        self.tx_batch.put(score_address, address.body, value)
        self.assertEqual(1, len(self.tx_batch))
        self.assertEqual(value, self.tx_batch[score_address][address.body])

        score_address = Address.from_string(f'cx{"7" * 40}')
        value = 7
        self.tx_batch.put(score_address, address.body, value)
        self.assertEqual(2, len(self.tx_batch))
        self.assertEqual(value, self.tx_batch[score_address][address.body])
