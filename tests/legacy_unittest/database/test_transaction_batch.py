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

from iconservice.base.exception import DatabaseException
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue, BlockBatchValue


class TestTransactionBatch(unittest.TestCase):
    def test_enter_call(self):
        tx_batch = TransactionBatch()
        call_count: int = tx_batch.call_count
        self.assertEqual(1, call_count)

        tx_batch.enter_call()
        self.assertEqual(call_count + 1, tx_batch.call_count)

        tx_batch[b'key'] = TransactionBatchValue(b'value', True)
        self.assertEqual(TransactionBatchValue(b'value', True), tx_batch[b'key'])

        tx_batch.leave_call()
        self.assertEqual(call_count, tx_batch.call_count)
        self.assertEqual(TransactionBatchValue(b'value', True), tx_batch[b'key'])

        tx_batch.enter_call()
        self.assertEqual(call_count + 1, tx_batch.call_count)

        tx_batch[b'id'] = TransactionBatchValue(b'hello', True)
        self.assertEqual(TransactionBatchValue(b'hello', True), tx_batch[b'id'])
        self.assertEqual(TransactionBatchValue(b'value', True), tx_batch[b'key'])

        tx_batch.revert_call()
        self.assertEqual(None, tx_batch[b'id'])
        self.assertEqual(TransactionBatchValue(b'value', True), tx_batch[b'key'])
        self.assertEqual(call_count + 1, tx_batch.call_count)

        tx_batch.leave_call()
        self.assertEqual(None, tx_batch[b'id'])
        self.assertEqual(TransactionBatchValue(b'value', True), tx_batch[b'key'])
        self.assertEqual(call_count, tx_batch.call_count)

    def test_iter(self):
        tx_batch = TransactionBatch()
        tx_batch[b'key0'] = TransactionBatchValue(b'value0', True)

        tx_batch.enter_call()
        tx_batch[b'key1'] = TransactionBatchValue(b'value1', True)

        keys = []
        for key in tx_batch:
            keys.append(key)

        self.assertEqual(b'key0', keys[0])
        self.assertEqual(b'key1', keys[1])

    def test_set_item(self):
        tx_batch = TransactionBatch()
        init_call_count = tx_batch.call_count
        self.assertEqual(0, len(tx_batch))
        self.assertEqual(1, init_call_count)

        tx_batch[b'key0'] = TransactionBatchValue(b'value0', True)
        self.assertEqual(1, len(tx_batch))

        tx_batch.enter_call()
        tx_batch[b'key1'] = TransactionBatchValue(b'value1', True)
        self.assertEqual(2, len(tx_batch))
        self.assertEqual(init_call_count + 1, tx_batch.call_count)

        tx_batch.enter_call()
        tx_batch[b'key0'] = TransactionBatchValue(None, True)
        tx_batch[b'key1'] = TransactionBatchValue(b'key1', True)
        tx_batch[b'key2'] = TransactionBatchValue(b'value2', True)
        self.assertEqual(5, len(tx_batch))
        self.assertEqual(init_call_count + 2, tx_batch.call_count)

        tx_batch.leave_call()
        self.assertEqual(4, len(tx_batch))
        self.assertEqual(TransactionBatchValue(b'key1', True), tx_batch[b'key1'])
        self.assertEqual(init_call_count + 1, tx_batch.call_count)

        tx_batch.leave_call()
        self.assertEqual(3, len(tx_batch))
        self.assertEqual(TransactionBatchValue(None, True), tx_batch[b'key0'])
        self.assertEqual(TransactionBatchValue(b'key1', True), tx_batch[b'key1'])
        self.assertEqual(TransactionBatchValue(b'value2', True), tx_batch[b'key2'])
        self.assertEqual(init_call_count, tx_batch.call_count)

    def test_delitem(self):
        tx_batch = TransactionBatch()
        tx_batch[b'key0'] = TransactionBatchValue(b'value0', True)

        with self.assertRaises(DatabaseException):
            del tx_batch[b'key0']

    def test_contains(self):
        tx_batch = TransactionBatch()
        init_call_count = tx_batch.call_count
        self.assertEqual(0, len(tx_batch))
        self.assertEqual(1, init_call_count)

        tx_batch[b'key0'] = TransactionBatchValue(b'value0', True)
        self.assertEqual(1, len(tx_batch))

        tx_batch.enter_call()
        tx_batch[b'key1'] = TransactionBatchValue(b'value1', True)
        self.assertEqual(2, len(tx_batch))
        self.assertEqual(init_call_count + 1, tx_batch.call_count)

        tx_batch.enter_call()
        tx_batch[b'key0'] = TransactionBatchValue(None, True)
        tx_batch[b'key1'] = TransactionBatchValue(b'key1', True)
        tx_batch[b'key2'] = TransactionBatchValue(b'value2', True)
        self.assertEqual(5, len(tx_batch))
        self.assertEqual(init_call_count + 2, tx_batch.call_count)

        keys = [b'key0', b'key1', b'key2']
        for key in keys:
            self.assertTrue(key in tx_batch)

        keys = [b'key3', b'key4']
        for key in keys:
            self.assertFalse(key in tx_batch)

        tx_batch = TransactionBatch()
        self.assertFalse(b'key' in tx_batch)

    def test_iterable(self):
        tx_batch = TransactionBatch()
        init_call_count = tx_batch.call_count
        self.assertEqual(0, len(tx_batch))
        self.assertEqual(1, init_call_count)

        tx_batch[b'key0'] = TransactionBatchValue(b'value0', True)
        self.assertEqual(1, len(tx_batch))

        block_batch = BlockBatch()
        block_batch.update(tx_batch)
        self.assertEqual(BlockBatchValue(b'value0', True, [-1]), block_batch[b'key0'])
