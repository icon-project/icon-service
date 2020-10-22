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
from typing import TYPE_CHECKING, Optional, Tuple, Iterable

import plyvel
from iconcommons.logger import Logger

from .batch import TransactionBatchValue
from ..base.exception import DatabaseException
from ..icon_constant import ICON_DB_LOG_TAG, IconScoreContextType

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


def _is_db_writable_on_context(context: 'IconScoreContext'):
    """Check if db is writable on a given context

    :param context:
    :return:
    """
    if context is None:
        return True
    else:
        return not context.readonly


class KeyValueDatabase(object):
    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'KeyValueDatabase':
        """

        :param path: db path
        :param create_if_missing:
        :return: KeyValueDatabase instance
        """
        db = plyvel.DB(path, create_if_missing=create_if_missing)
        return KeyValueDatabase(db)

    def __init__(self, db: plyvel.DB) -> None:
        """Constructor

        :param db: plyvel db instance
        """
        self._db = db

    def get(self, key: bytes) -> bytes:
        """Get the value for the specified key.

        :param key: (bytes): key to retrieve
        :return: value for the specified key, or None if not found
        """
        return self._db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """Set a value for the specified key.

        :param key: (bytes): key to set
        :param value: (bytes): data to be stored
        """
        self._db.put(key, value)

    def delete(self, key: bytes) -> None:
        """Delete the key/value pair for the specified key.

        :param key: key to delete
        """
        self._db.delete(key)

    def close(self) -> None:
        """Close the database.
        """
        if self._db:
            self._db.close()
            self._db = None

    def get_sub_db(self, prefix: bytes) -> 'KeyValueDatabase':
        """Return a new prefixed database.

        :param prefix: (bytes): prefix to use
        """
        return KeyValueDatabase(self._db.prefixed_db(prefix))

    def iterator(self) -> iter:
        return self._db.iterator()

    def write_batch(self, it: Iterable[Tuple[bytes, Optional[bytes]]]) -> int:
        """Write a batch to the database for the specified states dict.

        :param it: iterable which return tuple(key, value)
            key: bytes
            value: optional bytes
        :return: the number of key-value pairs written
        """
        size = 0

        if it is None:
            return size

        with self._db.write_batch() as wb:
            for key, value in it:
                if value:
                    wb.put(key, value)
                else:
                    wb.delete(key)

                size += 1

        return size


class DatabaseObserver(object):
    """ An abstract class of database observer.
    """

    def __init__(self,
                 get_func: callable, put_func: callable, delete_func: callable):
        self.__get_func = get_func
        self.__put_func = put_func
        self.__delete_func = delete_func

    def on_get(self, context: 'IconScoreContext', key: bytes, value: bytes):
        """
        Invoked when `get` is called in `ContextDatabase`

        :param context: SCORE context
        :param key: key
        :param value: value
        """
        if not self.__get_func:
            Logger.warning('__get_func is None', ICON_DB_LOG_TAG)
        self.__get_func(context, key, value)

    def on_put(self,
               context: 'IconScoreContext',
               key: bytes,
               old_value: bytes,
               new_value: bytes):
        """Invoked when `put` is called in `ContextDatabase`.

        :param context: SCORE context
        :param key: key
        :param old_value: old value
        :param new_value: new value
        """
        if not self.__put_func:
            Logger.warning('__put_func is None', ICON_DB_LOG_TAG)
        self.__put_func(context, key, old_value, new_value)

    def on_delete(self,
                  context: 'IconScoreContext',
                  key: bytes,
                  old_value: bytes):
        """Invoked when `delete` is called in `ContextDatabase`.


        :param context: SCORE context
        :param key: key
        :param old_value:
        """
        if not self.__delete_func:
            Logger.warning('__delete_func is None', ICON_DB_LOG_TAG)
        self.__delete_func(context, key, old_value)


class ContextDatabase(object):
    """Database for an IconScore only used in the inside of iconservice.

    IconScore cannot access this database directly.
    Cache + LevelDB
    """

    def __init__(self, db: 'KeyValueDatabase', is_shared: bool = False) -> None:
        """Constructor

        :param db: KeyValueDatabase instance
        """
        self.key_value_db = db
        # True: this db is shared with all smart contracts
        self._is_shared = is_shared

    def get(self, context: Optional['IconScoreContext'], key: bytes) -> bytes:
        """Returns value indicated by key from batch or StateDB

        :param context:
        :param key:
        :return: value
        """
        context_type = context.type

        if context_type in (IconScoreContextType.DIRECT, IconScoreContextType.QUERY):
            return self.key_value_db.get(key)
        else:
            return self.get_from_batch(context, key)

    def get_from_batch(self,
                       context: 'IconScoreContext',
                       key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. Current BlockBatch
        3. Prev BlockBatch
        4. StateDB

        :param context:
        :param key:

        :return: a value for a given key
        """
        # Find the value from tx_batch, block_batch and prev_block_batches with a given key
        for batch in context.get_batches():
            if key in batch:
                return batch[key].value

        # get value from state_db
        return self.key_value_db.get(key)

    @staticmethod
    def _check_tx_batch_value(context: Optional['IconScoreContext'],
                              key: bytes,
                              include_state_root_hash: bool):
        tx_batch_value: 'TransactionBatchValue' = context.tx_batch.get(key)
        if tx_batch_value is None:
            return

        if not isinstance(tx_batch_value, TransactionBatchValue):
            raise DatabaseException(
                f'Only TransactionBatchValue type is allowed on tx_batch: {type(tx_batch_value)}')
        elif tx_batch_value.include_state_root_hash != include_state_root_hash:
            raise DatabaseException('Do not change the include_state_root_hash on the same data')

    def put(self,
            context: Optional['IconScoreContext'],
            key: bytes,
            value: Optional[bytes]) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        :param value:
        """
        self._put(context, key, value, include_state_root_hash=True)

    def _put(self,
             context: Optional['IconScoreContext'],
             key: bytes,
             value: Optional[bytes],
             include_state_root_hash: bool) -> None:
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to write')

        context_type = context.type

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.put(key, value)
        else:
            self._check_tx_batch_value(context, key, include_state_root_hash)
            tx_index: int = context.tx.index if context.tx is not None else -1
            context.tx_batch[key] = TransactionBatchValue(value, include_state_root_hash, tx_index)

    def delete(self,
               context: Optional['IconScoreContext'],
               key: bytes):
        """Delete key from db

        :param context:
        :param key: key to delete from db
        """
        self._delete(context, key, include_state_root_hash=True)

    def _delete(self,
                context: Optional['IconScoreContext'],
                key: bytes,
                include_state_root_hash: bool):
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to delete')

        context_type = context.type

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.delete(key)
        else:
            self._check_tx_batch_value(context, key, include_state_root_hash)
            tx_index: int = context.tx.index if context.tx is not None else -1
            context.tx_batch[key] = TransactionBatchValue(None, include_state_root_hash, tx_index)

    def close(self, context: 'IconScoreContext') -> None:
        """close db

        :param context:
        """
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to close')

        if not self._is_shared:
            return self.key_value_db.close()

    def write_batch(self,
                    context: 'IconScoreContext',
                    it: Iterable[Tuple[bytes, Optional[bytes]]]):

        if not _is_db_writable_on_context(context):
            raise DatabaseException(
                'write_batch is not allowed on readonly context')

        return self.key_value_db.write_batch(it)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'ContextDatabase':
        db = KeyValueDatabase.from_path(path, create_if_missing)
        return ContextDatabase(db)


class MetaContextDatabase(ContextDatabase):
    def put(self,
            context: Optional['IconScoreContext'],
            key: bytes,
            value: Optional[bytes]) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        :param value:
        """
        self._put(context, key, value, include_state_root_hash=False)

    def delete(self,
               context: Optional['IconScoreContext'],
               key: bytes) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        """
        self._delete(context, key, include_state_root_hash=False)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'MetaContextDatabase':
        db = KeyValueDatabase.from_path(path, create_if_missing)
        return MetaContextDatabase(db)
