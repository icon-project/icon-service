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

from typing import TYPE_CHECKING, Optional

import plyvel

from iconcommons.logger import Logger
from ..base.exception import DatabaseException, InvalidParamsException
from ..icon_constant import ICON_DB_LOG_TAG
from ..iconscore.icon_score_context import ContextGetter, IconScoreContextType

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


def _get_context_type(context: 'IconScoreContext') -> 'IconScoreContextType':
    if context is None:
        return IconScoreContextType.DIRECT
    else:
        return context.type


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
                  create_if_missing: bool=True) -> 'KeyValueDatabase':
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

    def write_batch(self, states: dict) -> None:
        """Write a batch to the database for the specified states dict.

        :param states: key/value pairs
            key and value should be bytes type
        """
        if states is None or len(states) == 0:
            return

        with self._db.write_batch() as wb:
            for key, value in states.items():
                if value:
                    wb.put(key, value)
                else:
                    wb.delete(key)


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

    def __init__(self, db: 'KeyValueDatabase', is_shared: bool=False) -> None:
        """Constructor

        :param db: KeyValueDatabase instance
        """
        self.key_value_db = db
        # True: this db is shared with all SCOREs
        self._is_shared = is_shared

    def get(self, context: Optional['IconScoreContext'], key: bytes) -> bytes:
        """Returns value indicated by key from batch or StateDB

        :param context:
        :param key:
        :return: value
        """
        context_type = _get_context_type(context)

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
        2. BlockBatch
        3. StateDB

        :param context:
        :param key:

        :return: a value for a given key
        """
        block_batch = context.block_batch
        tx_batch = context.tx_batch

        # get value from tx_batch
        if key in tx_batch:
            return tx_batch[key]

        # get value from block_batch
        if key in block_batch:
            return block_batch[key]

        # get value from state_db
        return self.key_value_db.get(key)

    def put(self,
            context: Optional['IconScoreContext'],
            key: bytes,
            value: Optional[bytes]) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        :param value:
        """
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to write')

        context_type = _get_context_type(context)

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.put(key, value)
        else:
            context.tx_batch[key] = value

    def delete(self, context: Optional['IconScoreContext'], key: bytes):
        """Delete key from db

        :param context:
        :param key: key to delete from db
        """
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to delete')

        context_type = _get_context_type(context)

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.delete(key)
        else:
            context.tx_batch[key] = None

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
                    states: dict):

        if not _is_db_writable_on_context(context):
            raise DatabaseException(
                'write_batch is not allowed on readonly context')

        return self.key_value_db.write_batch(states)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool=True) -> 'ContextDatabase':
        db = KeyValueDatabase.from_path(path, create_if_missing)
        return ContextDatabase(db)


class IconScoreDatabase(ContextGetter):
    """It is used in IconScore

    IconScore can access its states only through IconScoreDatabase
    """
    def __init__(self,
                 address: 'Address',
                 context_db: 'ContextDatabase',
                 prefix: bytes=None) -> None:
        """Constructor

        :param address: the address of SCORE which this db is assigned to
        :param context_db: ContextDatabase
        :param prefix:
        """
        self.address = address
        self._prefix = prefix
        self._context_db = context_db
        self._observer: DatabaseObserver = None

    def get(self, key: bytes) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        hashed_key = self._hash_key(key)
        value = self._context_db.get(self._context, hashed_key)
        if self._observer:
            self._observer.on_get(self._context, key, value)
        return value

    def put(self, key: bytes, value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        hashed_key = self._hash_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, hashed_key)
            if value:
                self._observer.on_put(self._context, key, old_value, value)
            elif old_value:
                # If new value is None, then deletes the field
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.put(self._context, hashed_key, value)

    def get_sub_db(self, prefix: bytes) -> 'IconScoreSubDatabase':
        """
        Returns sub db with a prefix

        :param prefix: The prefix used by this sub db.
        :return: sub db
        """
        if prefix is None:
            raise InvalidParamsException(
                'Invalid params: '
                'prefix is None in IconScoreDatabase.get_sub_db()')

        if self._prefix is not None:
            prefix = b'|'.join([self._prefix, prefix])

        return IconScoreSubDatabase(self.address, self, prefix)

    def delete(self, key: bytes):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        hashed_key = self._hash_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, hashed_key)
            # If old value is None, won't fire the callback
            if old_value:
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.delete(self._context, hashed_key)

    def close(self):
        self._context_db.close(self._context)

    def set_observer(self, observer: 'DatabaseObserver'):
        self._observer = observer

    def _hash_key(self, key: bytes) -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """
        data = [self.address.to_bytes()]
        if self._prefix is not None:
            data.append(self._prefix)
        data.append(key)

        return b'|'.join(data)


class IconScoreSubDatabase(object):
    def __init__(self, address: 'Address', score_db: 'IconScoreDatabase', prefix: bytes):
        """Constructor

        :param address: the address of SCORE which this db is assigned to
        :param score_db: IconScoreDatabase
        :param prefix:
        """
        if prefix is None or len(prefix) == 0:
            raise InvalidParamsException("Invalid prefix")

        self.address = address
        self._prefix = prefix
        self._score_db = score_db

    def get(self, key: bytes) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        hashed_key = self._hash_key(key)
        return self._score_db.get(hashed_key)

    def put(self, key: bytes, value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        hashed_key = self._hash_key(key)
        self._score_db.put(hashed_key, value)

    def get_sub_db(self, prefix: bytes) -> 'IconScoreSubDatabase':
        """
        Returns sub db with a prefix

        :param prefix: The prefix used by this sub db.
        :return: sub db
        """
        if prefix is None:
            raise InvalidParamsException("Invalid prefix")

        if self._prefix is not None:
            prefix = b'|'.join([self._prefix, prefix])

        return IconScoreSubDatabase(self.address, self._score_db, prefix)

    def delete(self, key: bytes):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        hashed_key = self._hash_key(key)
        self._score_db.delete(hashed_key)

    def close(self):
        self._score_db.close()

    def _hash_key(self, key: bytes) -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """
        data = []
        if self._prefix is not None:
            data.append(self._prefix)
        data.append(key)

        return b'|'.join(data)
