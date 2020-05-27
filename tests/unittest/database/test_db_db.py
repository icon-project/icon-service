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
import threading
from unittest.mock import patch

import pytest
from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import DatabaseException, InvalidParamsException
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue
from iconservice.database.db import ContextDatabase, MetaContextDatabase
from iconservice.database.db import IconScoreDatabase
from iconservice.database.db import KeyValueDatabase
from iconservice.database.wal import StateWAL
from iconservice.icon_constant import DATA_BYTE_ORDER
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreFuncType
from tests import rmtree


@pytest.fixture(scope="function", params=[None, threading.Lock()])
def key_value_db(request):
    state_db_root_path = 'state_db'
    rmtree(state_db_root_path)
    os.mkdir(state_db_root_path)

    db = KeyValueDatabase.from_path(
        path=state_db_root_path,
        create_if_missing=True,
        lock=request.param
    )
    yield db

    db.close()
    rmtree(state_db_root_path)


@pytest.fixture(scope="function")
def context_db(key_value_db):
    return ContextDatabase(key_value_db, is_shared=True)


@pytest.fixture(scope="function")
def context():
    context = IconScoreContext(IconScoreContextType.INVOKE)
    context.block_batch = BlockBatch()
    context.tx_batch = TransactionBatch()
    return context


class TestKeyValueDatabase(object):
    def test_get_and_put(self, key_value_db):
        db = key_value_db

        db.put(b'key0', b'value0')
        value = db.get(b'key0')
        assert value == b'value0'

        value = db.get(b'key1')
        assert value is None

    def test_write_batch(self, key_value_db):
        db = key_value_db
        data = {
            b'key0': TransactionBatchValue(b'value0', True),
            b'key1': TransactionBatchValue(b'value1', True)
        }

        db.write_batch(StateWAL(data))

        assert db.get(b'key1') == b'value1'
        assert db.get(b'key0') == b'value0'


class TestContextDatabaseOnWriteMode:

    def test_put_and_get(self, context, context_db):
        """
        """
        address = Address.from_data(AddressPrefix.CONTRACT, b'score')

        value = 100
        context_db._put(context, address.body, value.to_bytes(32, 'big'), True)

        value = context_db.get(context, address.body)
        assert int.from_bytes(value, 'big') == 100

    def test_put(self, context, context_db):
        """WritableDatabase supports put()
        """
        context_db._put(context, b'key0', b'value0', True)
        value = context_db.get(context, b'key0')
        assert value == b'value0'

        batch = context.tx_batch
        assert batch[b'key0'] == (b'value0', True)

        context_db._put(context, b'key0', b'value1', True)
        context_db._put(context, b'key1', b'value1', True)

        assert len(batch) == 2
        assert batch[b'key0'] == (b'value1', True)
        assert batch[b'key1'] == (b'value1', True)

        context_db._put(context, b'key2', b'value2', False)
        context_db._put(context, b'key3', b'value3', False)

        value2 = context_db.get(context, b'key2')
        value3 = context_db.get(context, b'key3')
        assert value2 == b'value2'
        assert value3 == b'value3'

        assert len(batch) == 4
        assert batch[b'key2'] == (b'value2', False)
        assert batch[b'key3'] == (b'value3', False)

        # overwrite
        with pytest.raises(DatabaseException):
            context_db._put(context, b'key3', b'value3', True)
        with pytest.raises(DatabaseException):
            context_db._put(context, b'key3', b'value3', True)
            context_db._delete(context, b'key3')

    def test_put_on_readonly_exception(self, context, context_db):
        context.func_type = IconScoreFuncType.READONLY

        with pytest.raises(DatabaseException):
            context_db._put(context, b'key1', b'value1', True)

    def test_write_batch(self, context, context_db):
        data = {
            b'key0': TransactionBatchValue(b'value0', True),
            b'key1': TransactionBatchValue(b'value1', True)
        }
        db = context_db
        db.write_batch(context, StateWAL(data))

        assert db.get(context, b'key1') == b'value1'
        assert db.get(context, b'key0') == b'value0'

    def test_write_batch_invalid_value_format(self, context, context_db):
        db = context_db

        data_list = [
            {b'key0': b'value0'},
            {b'key0': None},
            {b'key0': ""},
        ]

        for data in data_list:
            with pytest.raises(InvalidParamsException):
                db.write_batch(context, StateWAL(data))

    def test_write_batch_on_readonly_exception(self, context, context_db):
        db = context_db
        context.func_type = IconScoreFuncType.READONLY

        with pytest.raises(DatabaseException):
            data = {
                b'key0': b'value0',
                b'key1': b'value1'
            }
            db.write_batch(context, data.items())

    def test_delete(self, context, context_db):
        db = context_db
        tx_batch = context.tx_batch
        state_wal = StateWAL(tx_batch)

        db._put(context, b'key0', b'value0', True)
        db._put(context, b'key1', b'value1', True)
        assert db.get(context, b'key0') == b'value0'
        assert tx_batch[b'key0'] == (b'value0', True)

        db.write_batch(context, state_wal)
        tx_batch.clear()
        assert len(tx_batch) == 0
        assert db.get(context, b'key0') == b'value0'

        db._delete(context, b'key0', True)
        db._delete(context, b'key1', False)
        assert db.get(context, b'key0') is None
        assert db.get(context, b'key1') is None
        assert tx_batch[b'key0'] == (None, True)
        assert tx_batch[b'key1'] == (None, False)
        db.write_batch(context, state_wal)
        tx_batch.clear()
        assert len(tx_batch) == 0
        assert db.get(context, b'key0') is None
        assert db.get(context, b'key1') is None

    def test_delete_on_readonly_exception(self, context, context_db):
        db = context_db
        tx_batch = context.tx_batch

        db._put(context, b'key0', b'value0', True)
        assert db.get(context, b'key0') == b'value0'
        assert tx_batch[b'key0'] == (b'value0', True)

        context.func_type = IconScoreFuncType.READONLY
        with pytest.raises(DatabaseException):
            db._delete(context, b'key0', True)

        context.func_type = IconScoreFuncType.WRITABLE
        db._delete(context, b'key0', True)
        assert db.get(context, b'key0') is None
        assert tx_batch[b'key0'] == (None, True)

    def test_put_and_delete_of_meta_context_db(self, context, key_value_db):
        context_db = ContextDatabase(key_value_db, is_shared=True)
        meta_context_db = MetaContextDatabase(key_value_db, is_shared=True)

        context_db.put(context, b'c_key', b'value0')
        meta_context_db.put(context, b'm_key', b'value0')
        assert context.tx_batch[b'c_key'] == (b'value0', True)
        assert context.tx_batch[b'm_key'] == (b'value0', False)

        context_db.delete(context, b'c_key')
        meta_context_db.delete(context, b'm_key')
        assert context.tx_batch[b'c_key'] == (None, True)
        assert context.tx_batch[b'm_key'] == (None, False)


class TestIconScoreDatabase:
    @patch('iconservice.iconscore.context.context.ContextGetter._context')
    def test_put_and_get(self, context, context_db):
        address = Address.from_data(AddressPrefix.CONTRACT, b'0')
        context.current_address = address
        key = address.body
        value = 100

        db = IconScoreDatabase(address, context_db=context_db, prefix=b'')
        assert db.address == address

        assert db.get(key) is None

        context.readonly = False
        context.type = IconScoreContextType.DIRECT
        db.put(key, value.to_bytes(32, DATA_BYTE_ORDER))
        assert db.get(key) == value.to_bytes(32, DATA_BYTE_ORDER)
