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

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import DatabaseException
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.database.db import ContextDatabase
from iconservice.database.db import IconScoreDatabase
from iconservice.database.db import KeyValueDatabase
from iconservice.icon_constant import DATA_BYTE_ORDER
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
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
            b'key0': b'value0',
            b'key1': b'value1'
        }
        db = self.db

        db.write_batch(data)

        self.assertEqual(b'value1', db.get(b'key1'))
        self.assertEqual(b'value0', db.get(b'key0'))


class TestContextDatabaseOnWriteMode(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = Address.from_data(AddressPrefix.CONTRACT, b'score')
        context_factory = IconScoreContextFactory(max_size=2)

        context = context_factory.create(IconScoreContextType.INVOKE)
        context.block_batch = BlockBatch()
        context.tx_batch = TransactionBatch()

        db_path = os.path.join(state_db_root_path, 'db')
        context_db = ContextDatabase.from_path(db_path, True)

        self.context_factory = context_factory
        self.context_db = context_db
        self.address = address
        self.context = context

    def tearDown(self):
        self.context.func_type = IconScoreFuncType.WRITABLE
        self.context_db.close(self.context)
        self.context_factory.destroy(self.context)
        rmtree(self.state_db_root_path)

    def test_put_and_get(self):
        """
        """
        context = self.context
        address = Address.from_data(AddressPrefix.CONTRACT, b'score')

        value = 100
        self.context_db.put(context, address.body, value.to_bytes(32, 'big'))

        value = self.context_db.get(context, address.body)
        self.assertEqual(100, int.from_bytes(value, 'big'))

    def test_put(self):
        """WritableDatabase supports put()
        """
        context = self.context
        self.context_db.put(context, b'key0', b'value0')
        value = self.context_db.get(context, b'key0')
        self.assertEqual(b'value0', value)

        batch = self.context.tx_batch
        self.assertEqual(b'value0', batch[b'key0'])

        self.context_db.put(context, b'key0', b'value1')
        self.context_db.put(context, b'key1', b'value1')

        self.assertEqual(len(batch), 2)
        self.assertEqual(batch[b'key0'], b'value1')
        self.assertEqual(batch[b'key1'], b'value1')

    def test_put_on_readonly_exception(self):
        context = self.context
        context.func_type = IconScoreFuncType.READONLY

        with self.assertRaises(DatabaseException):
            self.context_db.put(context, b'key1', b'value1')

    def test_write_batch(self):
        context = self.context
        data = {
            b'key0': b'value0',
            b'key1': b'value1'
        }
        db = self.context_db
        db.write_batch(context, data)

        self.assertEqual(b'value1', db.get(context, b'key1'))
        self.assertEqual(b'value0', db.get(context, b'key0'))

    def test_write_batch_on_readonly_exception(self):
        db = self.context_db
        context = self.context
        context.func_type = IconScoreFuncType.READONLY

        with self.assertRaises(DatabaseException):
            data = {
                b'key0': b'value0',
                b'key1': b'value1'
            }
            db.write_batch(context, data)

    def test_none_context(self):
        context = None
        db = self.context_db

        db.put(context, b'key0', b'value0')
        self.assertEqual(b'value0', db.get(context, b'key0'))

        db.delete(context, b'key0')
        self.assertIsNone(db.get(context, b'key0'))

        with self.assertRaises(TypeError):
            db.put(context, b'key1', None)

    def test_delete(self):
        context = self.context        
        db = self.context_db
        tx_batch = context.tx_batch

        db.put(context, b'key0', b'value0')
        self.assertEqual(b'value0', db.get(context, b'key0'))
        self.assertEqual(b'value0', tx_batch[b'key0'])

        db.write_batch(context, tx_batch)
        tx_batch.clear()
        self.assertEqual(0, len(tx_batch))
        self.assertEqual(b'value0', db.get(context, b'key0'))

        db.delete(context, b'key0')
        db.write_batch(context, tx_batch)
        tx_batch.clear()
        self.assertEqual(0, len(tx_batch))
        self.assertIsNone(db.get(context, b'key0'))

    def test_delete_on_readonly_exception(self):
        context = self.context
        db = self.context_db
        tx_batch = context.tx_batch

        db.put(context, b'key0', b'value0')
        self.assertEqual(b'value0', db.get(context, b'key0'))
        self.assertEqual(b'value0', tx_batch[b'key0'])

        context.func_type = IconScoreFuncType.READONLY
        with self.assertRaises(DatabaseException):
            db.delete(context, b'key0')

        context.func_type = IconScoreFuncType.WRITABLE
        db.delete(context, b'key0')
        self.assertIsNone(tx_batch[b'key0'])


class TestIconScoreDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = Address.from_data(AddressPrefix.CONTRACT, b'0')
        context_factory = IconScoreContextFactory(max_size=2)

        db_path = os.path.join(state_db_root_path, 'db')
        context_db = ContextDatabase.from_path(db_path, True)

        self.db = IconScoreDatabase(address, context_db=context_db, prefix=b'')
        self.address = address
        self.context_factory = context_factory

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_address(self):
        self.assertEqual(self.address, self.db.address)

    def test_put_and_get(self):
        db = self.db
        key = self.address.body
        value = 100

        self.assertIsNone(db.get(key))

        db.put(key, value.to_bytes(32, DATA_BYTE_ORDER))
        self.assertEqual(value.to_bytes(32, DATA_BYTE_ORDER), db.get(key))
