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

from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.utils import sha3_256
from tests import create_hash_256


class TestBatch(unittest.TestCase):
    def setUp(self):
        self.block_hash: bytes = create_hash_256()
        self.prev_block_hash: bytes = create_hash_256()

        block = Block(
            block_height=10,
            block_hash=self.block_hash,
            timestamp=0,
            prev_hash=self.prev_block_hash,
            cumulative_fee=0)

        self.block_batch = BlockBatch(block)

    def test_property(self):
        self.assertEqual(10, self.block_batch.block.height)
        self.assertEqual(0, self.block_batch.block.timestamp)
        self.assertEqual(self.block_hash, self.block_batch.block.hash)
        self.assertEqual(
            self.prev_block_hash, self.block_batch.block.prev_hash)

    def test_len(self):
        key = create_hash_256()

        self.block_batch[key] = b'value0'
        self.assertEqual(1, len(self.block_batch))

        self.block_batch[key] = b'value1'
        self.assertEqual(1, len(self.block_batch))

        key1 = create_hash_256()
        self.block_batch[key1] = b'value1'
        self.assertEqual(2, len(self.block_batch))

        del self.block_batch[key]
        self.assertEqual(1, len(self.block_batch))

        del self.block_batch[key1]
        self.assertEqual(0, len(self.block_batch))

    def test_get_item(self):
        byteorder = 'big'
        key = create_hash_256()

        self.block_batch[key] = b'value'
        self.assertEqual(b'value', self.block_batch[key])

        value = 100
        self.block_batch[key] = value.to_bytes(8, byteorder)
        self.assertEqual(
            value,
            int.from_bytes(self.block_batch[key], byteorder))

    def test_put_tx_batch(self):
        tx_hash = create_hash_256()
        tx_batch = TransactionBatch(tx_hash)

        key = create_hash_256()
        tx_batch[key] = b'value'

        key0 = create_hash_256()
        tx_batch[key0] = b'value0'
        key1 = create_hash_256()
        tx_batch[key1] = b'value1'
        key2 = create_hash_256()
        tx_batch[key2] = b'value2'

        self.assertEqual(4, len(tx_batch))

        self.block_batch[key] = b'haha'
        self.assertEqual(1, len(self.block_batch))

        self.block_batch.update(tx_batch)

        self.assertEqual(4, len(self.block_batch))
        self.assertEqual(b'value0', self.block_batch[key0])
        self.assertEqual(b'value1', self.block_batch[key1])
        self.assertEqual(b'value2', self.block_batch[key2])
        self.assertEqual(b'value', self.block_batch[key])

    def test_digest(self):
        block_batch = self.block_batch

        key0 = create_hash_256()
        block_batch[key0] = b'value0'
        key1 = create_hash_256()
        block_batch[key1] = b'value1'
        key2 = create_hash_256()
        block_batch[key2] = b'value2'

        data = [key0, b'value0', key1, b'value1', key2, b'value2']
        expected = sha3_256(b'|'.join(data))
        ret = block_batch.digest()
        self.assertEqual(expected, ret)

        block_batch[key2] = None
        hash1 = block_batch.digest()
        block_batch[key2] = b''
        hash2 = block_batch.digest()
        self.assertNotEqual(hash1, hash2)

    def test_digest_with_excluded_data(self):
        block_batch = self.block_batch

        include_key1 = create_hash_256()
        block_batch[include_key1] = (b'value0', True)
        include_key2 = create_hash_256()
        block_batch[include_key2] = (b'value1', True)
        exclude_key1 = create_hash_256()
        block_batch[exclude_key1] = (b'value2', False)
        exclude_key2 = create_hash_256()
        block_batch[exclude_key2] = (b'value3', False)

        data = [include_key1, b'value0', include_key2, b'value1']
        expected = sha3_256(b'|'.join(data))
        ret = block_batch.digest()
        self.assertEqual(expected, ret)
