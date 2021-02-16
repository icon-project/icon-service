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


import os
import unittest
from unittest.mock import patch

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import DatabaseException, InvalidParamsException
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue, BlockBatchValue
from iconservice.database.db import ContextDatabase, MetaContextDatabase
from iconservice.database.db import KeyValueDatabase
from iconservice.database.wal import StateWAL
from iconservice.icon_constant import Revision
from iconservice.iconscore.db import IconScoreDatabase
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreFuncType
from tests import rmtree


class TestKeyValueDatabase(unittest.TestCase):

    def setUp(self):
        self.state_db_root_path = 'state_db'
        rmtree(self.state_db_root_path)
        os.mkdir(self.state_db_root_path)

        self.db = KeyValueDatabase.from_path(self.state_db_root_path, True)

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_get_and_put(self):
        db = self.db

        db.put(b'key0', b'value0')
        value = db.get(b'key0')
        self.assertEqual(b'value0', value)

        value = db.get(b'key1')
        self.assertIsNone(value)

    def test_write_batch(self):
        data = {
            b'key0': BlockBatchValue(b'value0', True, [-1]),
            b'key1': BlockBatchValue(b'value1', True, [-1])
        }
        db = self.db

        db.write_batch(StateWAL(data))

        self.assertEqual(b'value1', db.get(b'key1'))
        self.assertEqual(b'value0', db.get(b'key0'))


class TestContextDatabaseOnWriteMode(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = Address.from_data(AddressPrefix.CONTRACT, b'score')

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.block_batch = BlockBatch()
        context.tx_batch = TransactionBatch()

        db_path = os.path.join(state_db_root_path, 'db')
        context_db = ContextDatabase.from_path(db_path, True)
        meta_context_db = MetaContextDatabase(context_db.key_value_db)
        self.context_db = context_db
        self.meta_context_db = meta_context_db
        self.address = address
        self.context = context

    def tearDown(self):
        self.context.func_type = IconScoreFuncType.WRITABLE
        self.context_db.close(self.context)
        rmtree(self.state_db_root_path)

    def test_put_and_get(self):
        """
        """
        context = self.context
        address = Address.from_data(AddressPrefix.CONTRACT, b'score')

        value = 100
        self.context_db._put(context, address.body, value.to_bytes(32, 'big'), True)

        value = self.context_db.get(context, address.body)
        self.assertEqual(100, int.from_bytes(value, 'big'))

    def test_put(self):
        """WritableDatabase supports put()
        """
        context = self.context
        self.context_db._put(context, b'key0', b'value0', True)
        value = self.context_db.get(context, b'key0')
        self.assertEqual(b'value0', value)

        batch = self.context.tx_batch
        self.assertEqual(TransactionBatchValue(b'value0', True), batch[b'key0'])

        self.context_db._put(context, b'key0', b'value1', True)
        self.context_db._put(context, b'key1', b'value1', True)

        self.assertEqual(len(batch), 2)
        self.assertEqual(batch[b'key0'], TransactionBatchValue(b'value1', True))
        self.assertEqual(batch[b'key1'], TransactionBatchValue(b'value1', True))

        self.context_db._put(context, b'key2', b'value2', False)
        self.context_db._put(context, b'key3', b'value3', False)

        value2 = self.context_db.get(context, b'key2')
        value3 = self.context_db.get(context, b'key3')
        self.assertEqual(b'value2', value2)
        self.assertEqual(b'value3', value3)

        self.assertEqual(len(batch), 4)
        self.assertEqual(batch[b'key2'], TransactionBatchValue(b'value2', False))
        self.assertEqual(batch[b'key3'], TransactionBatchValue(b'value3', False))

        # overwrite
        self.assertRaises(DatabaseException, self.context_db._put, context, b'key3', b'value3', True)
        self.assertRaises(DatabaseException, self.context_db._delete, context, b'key3', True)

    def test_put_on_readonly_exception(self):
        context = self.context
        context.func_type = IconScoreFuncType.READONLY

        with self.assertRaises(DatabaseException):
            self.context_db._put(context, b'key1', b'value1', True)

    def test_write_batch(self):
        context = self.context
        data = {
            b'key0': BlockBatchValue(b'value0', True, [-1]),
            b'key1': BlockBatchValue(b'value1', True, [-1])
        }
        db = self.context_db
        db.write_batch(context, StateWAL(data))

        self.assertEqual(b'value1', db.get(context, b'key1'))
        self.assertEqual(b'value0', db.get(context, b'key0'))

    def test_write_batch_invalid_value_format(self):
        context = self.context
        data = {
            b'key0': b'value0',
        }
        db = self.context_db
        with self.assertRaises(InvalidParamsException):
            db.write_batch(context, StateWAL(data))

        data = {
            b'key0': None,
        }
        db = self.context_db
        with self.assertRaises(InvalidParamsException):
            db.write_batch(context, StateWAL(data))

        data = {
            b'key0': "",
        }
        db = self.context_db
        with self.assertRaises(InvalidParamsException):
            db.write_batch(context, StateWAL(data))

    def test_write_batch_on_readonly_exception(self):
        db = self.context_db
        context = self.context
        context.func_type = IconScoreFuncType.READONLY

        with self.assertRaises(DatabaseException):
            data = {
                b'key0': b'value0',
                b'key1': b'value1'
            }
            db.write_batch(context, data.items())

    @unittest.skip('context is never none')
    def test_none_context(self):
        context = None
        db = self.context_db

        db._put(context, b'key0', b'value0', True)
        self.assertEqual(b'value0', db.get(context, b'key0'))

        db.delete(context, b'key0')
        self.assertIsNone(db.get(context, b'key0'))

        with self.assertRaises(TypeError):
            db._put(context, b'key1', None, True)

    def test_delete(self):
        context = self.context
        db = self.context_db
        tx_batch = context.tx_batch
        block_batch = context.block_batch

        db._put(context, b'key0', b'value0', True)
        db._put(context, b'key1', b'value1', True)
        self.assertEqual(b'value0', db.get(context, b'key0'))
        self.assertEqual(TransactionBatchValue(b'value0', True), tx_batch[b'key0'])

        block_batch.update(tx_batch)
        state_wal = StateWAL(block_batch)
        db.write_batch(context, state_wal)
        tx_batch.clear()
        block_batch.clear()

        self.assertEqual(0, len(tx_batch))
        self.assertEqual(b'value0', db.get(context, b'key0'))

        db._delete(context, b'key0', True)
        db._delete(context, b'key1', False)
        self.assertEqual(None, db.get(context, b'key0'))
        self.assertEqual(None, db.get(context, b'key1'))
        self.assertEqual(TransactionBatchValue(None, True), tx_batch[b'key0'])
        self.assertEqual(TransactionBatchValue(None, False), tx_batch[b'key1'])
        block_batch.update(tx_batch)
        db.write_batch(context, state_wal)
        tx_batch.clear()
        block_batch.clear()

        self.assertEqual(0, len(tx_batch))
        self.assertIsNone(db.get(context, b'key0'))
        self.assertIsNone(db.get(context, b'key1'))

    def test_delete_on_readonly_exception(self):
        context = self.context
        db = self.context_db
        tx_batch = context.tx_batch

        db._put(context, b'key0', b'value0', True)
        self.assertEqual(b'value0', db.get(context, b'key0'))
        self.assertEqual(TransactionBatchValue(b'value0', True), tx_batch[b'key0'])

        context.func_type = IconScoreFuncType.READONLY
        with self.assertRaises(DatabaseException):
            db._delete(context, b'key0', True)

        context.func_type = IconScoreFuncType.WRITABLE
        db._delete(context, b'key0', True)
        self.assertIsNone(db.get(context, b'key0'))
        self.assertEqual(TransactionBatchValue(None, True), tx_batch[b'key0'])

    def test_put_and_delete_of_meta_context_db(self):
        context = self.context
        context_db = self.context_db
        meta_context_db = self.meta_context_db

        context_db.put(context, b'c_key', b'value0')
        meta_context_db.put(context, b'm_key', b'value0')
        self.assertEqual(TransactionBatchValue(b'value0', True), context.tx_batch[b'c_key'])
        self.assertEqual(TransactionBatchValue(b'value0', False), context.tx_batch[b'm_key'])

        context_db.delete(context, b'c_key')
        meta_context_db.delete(context, b'm_key')
        self.assertEqual(TransactionBatchValue(None, True), context.tx_batch[b'c_key'])
        self.assertEqual(TransactionBatchValue(None, False), context.tx_batch[b'm_key'])


class TestIconScoreDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = Address.from_data(AddressPrefix.CONTRACT, b'0')

        db_path = os.path.join(state_db_root_path, 'db')
        context_db = ContextDatabase.from_path(db_path, True)

        self.db = IconScoreDatabase(address, context_db=context_db)
        self.address = address

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_address(self):
        self.assertEqual(self.address, self.db.address)

    @patch('iconservice.iconscore.context.context.ContextGetter._context')
    def test_put_and_get(self, context):
        context.current_address = self.address
        context.revision = Revision.USE_RLP.value - 1
        context.type = IconScoreContextType.DIRECT
        context.readonly = False

        db = self.db
        for i in range(3):
            key = f"key{i}".encode()
            self.assertIsNone(db.get(key))

        for i in range(3):
            key = f"key{i}".encode()
            value = i.to_bytes(20, "big")

            self.assertIsNone(db.get(key))
            db.put(key, value)
            self.assertEqual(value, db.get(key))

        context.revision = Revision.USE_RLP.value

        for i in range(3):
            key = f"key{i}".encode()
            old_value = i.to_bytes(20, "big")
            new_value = i.to_bytes(30, "big")
            self.assertNotEqual(old_value, new_value)

            self.assertEqual(old_value, db.get(key))
            db.put(key, new_value)
            self.assertEqual(new_value, db.get(key))
