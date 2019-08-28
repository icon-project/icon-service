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
from iconservice.base.exception import IllegalFormatException, DatabaseException, AccessDeniedException
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue
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

    def test_data_format(self):
        # Cannot set data to block batch directly
        key = create_hash_256()
        with self.assertRaises(AccessDeniedException):
            self.block_batch[key] = b'value0'

    def test_block_batch_direct_put(self):
        key = create_hash_256()
        with self.assertRaises(AccessDeniedException):
            self.block_batch[key] = (b'value', True)

    def test_len(self):
        key = create_hash_256()

        tx_batch = TransactionBatch(create_hash_256())
        tx_batch[key] = TransactionBatchValue(b'value0', True)
        self.block_batch.update(tx_batch)
        self.assertEqual(1, len(self.block_batch))

        tx_batch[key] = TransactionBatchValue(b'value1', True)
        self.block_batch.update(tx_batch)
        self.assertEqual(1, len(self.block_batch))

        key1 = create_hash_256()
        tx_batch[key1] = TransactionBatchValue(b'value0', True)
        self.block_batch.update(tx_batch)
        self.assertEqual(2, len(self.block_batch))

        del self.block_batch[key]
        self.assertEqual(1, len(self.block_batch))

        del self.block_batch[key1]
        self.assertEqual(0, len(self.block_batch))

    def test_get_item(self):
        byteorder = 'big'

        key = create_hash_256()
        tx_batch = TransactionBatch(create_hash_256())
        tx_batch[key] = (b'value', True)
        self.block_batch.update(tx_batch)
        self.assertEqual((b'value', True), self.block_batch[key])

        value = 100
        tx_batch[key] = (value.to_bytes(8, byteorder), True)
        self.block_batch.update(tx_batch)
        self.assertEqual(
            value,
            int.from_bytes(self.block_batch[key][0], byteorder))

    def test_put_tx_batch(self):
        tx_hash = create_hash_256()
        tx_batch = TransactionBatch(tx_hash)

        key = create_hash_256()
        tx_batch[key] = (b'value', True)

        key0 = create_hash_256()
        tx_batch[key0] = (b'value0', True)
        key1 = create_hash_256()
        tx_batch[key1] = (b'value1', True)
        key2 = create_hash_256()
        tx_batch[key2] = (b'value2', True)

        self.assertEqual(4, len(tx_batch))

        tx_batch_2 = TransactionBatch(tx_hash)
        tx_batch_2[key] = (b'haha', True)
        self.block_batch.update(tx_batch_2)
        self.assertEqual(1, len(self.block_batch))

        self.block_batch.update(tx_batch)

        self.assertEqual(4, len(self.block_batch))
        self.assertEqual((b'value0', True), self.block_batch[key0])
        self.assertEqual((b'value1', True), self.block_batch[key1])
        self.assertEqual((b'value2', True), self.block_batch[key2])
        self.assertEqual((b'value', True), self.block_batch[key])

    def test_digest(self):
        block_batch = self.block_batch

        tx_batch = TransactionBatch(create_hash_256())
        key0 = create_hash_256()
        tx_batch[key0] = TransactionBatchValue(b'value0', True)
        key1 = create_hash_256()
        tx_batch[key1] = TransactionBatchValue(b'value1', True)
        key2 = create_hash_256()
        tx_batch[key2] = TransactionBatchValue(b'value2', True)

        block_batch.update(tx_batch)
        data = [key0, b'value0', key1, b'value1', key2, b'value2']
        expected = sha3_256(b'|'.join(data))
        ret = block_batch.digest()
        self.assertEqual(expected, ret)

        tx_batch[key2] = TransactionBatchValue(None, True)
        block_batch.update(tx_batch)
        hash1 = block_batch.digest()

        tx_batch[key2] = TransactionBatchValue(b'', True)
        block_batch.update(tx_batch)
        hash2 = block_batch.digest()
        self.assertNotEqual(hash1, hash2)

    def test_digest_with_excluded_data(self):
        block_batch = self.block_batch

        tx_batch = TransactionBatch(create_hash_256())
        include_key1 = create_hash_256()
        tx_batch[include_key1] = TransactionBatchValue(b'value0', True)
        include_key2 = create_hash_256()
        tx_batch[include_key2] = TransactionBatchValue(b'value1', True)
        include_key3 = create_hash_256()
        tx_batch[include_key3] = TransactionBatchValue(b'', True)
        include_key4 = create_hash_256()
        tx_batch[include_key4] = TransactionBatchValue(None, True)

        exclude_key1 = create_hash_256()
        tx_batch[exclude_key1] = TransactionBatchValue(b'value2', False)
        exclude_key2 = create_hash_256()
        tx_batch[exclude_key2] = TransactionBatchValue(b'value3', False)

        block_batch.update(tx_batch)
        data = [include_key1, b'value0', include_key2, b'value1', include_key3, b'', include_key4]
        expected = sha3_256(b'|'.join(data))
        ret = block_batch.digest()
        self.assertEqual(expected, ret)
