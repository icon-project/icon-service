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
from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch


class TestBlockBatch(unittest.TestCase):
    def setUp(self):
        self.batch = \
            BlockBatch(block=Block(0, 'd1e7281723bfa4c9e358080bfe57a6c36c67eba94a974d8a2ea4c3cdb0229399', 0, ''))

        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.batch.put(score_address, address, 1)

    def test_property(self):
        self.assertEqual(0, self.batch.block.height)
        self.assertEqual(
            'd1e7281723bfa4c9e358080bfe57a6c36c67eba94a974d8a2ea4c3cdb0229399',
            self.batch.block.hash)

    def test_len(self):
        self.assertEqual(1, len(self.batch))

    def test_get_item(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.assertEqual(1, self.batch[score_address][address])

    def test_put_tx_batch(self):
        tx_batch = TransactionBatch('')

        score_address = Address.from_string(f'cx{"f" * 40}')
        address = Address.from_string(f'hx{"2" * 40}')
        tx_batch.put(score_address, address, 2)
        address = Address.from_string(f'hx{"3" * 40}')
        tx_batch.put(score_address, address, 3)
        self.batch.put_tx_batch(tx_batch)

        self.assertEqual(2, len(self.batch))

        address = Address.from_string(f'hx{"2" * 40}')
        self.assertEqual(2, self.batch[score_address][address])
        address = Address.from_string(f'hx{"3" * 40}')
        self.assertEqual(3, self.batch[score_address][address])

        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.assertEqual(1, self.batch[score_address][address])

    def test_put(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        self.assertEqual(1, len(self.batch[score_address]))

        address = Address.from_string(f'hx{"2" * 40}')
        self.batch.put(score_address, address, 2)
        self.assertEqual(1, len(self.batch))
        self.assertEqual(2, self.batch[score_address][address])
        self.assertEqual(2, len(self.batch[score_address]))

        score_address = Address.from_string(f'cx{"b" * 40}')
        address = Address.from_string(f'hx{"2" * 40}')
        self.batch.put(score_address, address, 100)
        self.assertEqual(2, len(self.batch))
        self.assertEqual(100, self.batch[score_address][address])
