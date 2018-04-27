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

import abc
import plyvel
import threading

from iconservice.base.address import Address
from iconservice.base.exception import DatabaseException
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.iconscore.icon_score_context import IconScoreContext


class IconServiceDatabase(abc.ABC):

    @abc.abstractmethod
    def get(self, key: bytes) -> bytes:
        pass

    @abc.abstractmethod
    def put(self, key: bytes, value: bytes):
        pass

    @abc.abstractmethod
    def delete(self, key: bytes):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    @abc.abstractmethod
    def get_sub_db(self, key: bytes):
        pass

    @abc.abstractmethod
    def iterator(self):
        pass

    @abc.abstractmethod
    def write_batch(self, states: dict):
        pass


class PlyvelDatabase(object):
    """Plyvel database wrapper
    """

    @staticmethod
    def make_db(path: str, create_if_missing: bool=True) -> plyvel.DB:
        return plyvel.DB(path, create_if_missing=create_if_missing)

    def __init__(self, db: plyvel.DB) -> None:
        """Constructor

        :param path: db directory path
        :param create_if_missing: if not exist, create db in path
        """
        self._db = db

    def get(self, key: bytes) -> bytes:
        """Get value from db using key

        :param key: db key
        :return: value indicated by key otherwise None
        """
        return self._db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """Put value into db using key.

        :param key: (bytes): db key
        :param value: (bytes): db에 저장할 데이터
        """
        self._db.put(key, value)

    def delete(self, key: bytes) -> None:
        """Delete a row

        :param key: delete the row indicated by key.
        """
        self._db.delete(key)

    def close(self) -> None:
        """Close db
        """
        if self._db:
            self._db.close()
            self._db = None

    def get_sub_db(self, key: bytes):
        """Get Prefixed db

        :param key: (bytes): prefixed_db key
        """

        return PlyvelDatabase(self._db.prefixed_db(key))

    def iterator(self) -> iter:
        return self._db.iterator()

    def write_batch(self, states: dict) -> None:
        """bulk data modification

        :param states: key:value pairs
            key and value should be bytes type
        """
        if states is None or len(states) == 0:
            return

        with self._db.write_batch() as wb:
            for key in states:
                wb.put(key, states[key])


class WritableDatabase(PlyvelDatabase):
    """Cache + LevelDB
    """

    def __init__(self, db: plyvel.DB, address: Address) -> None:
        """Constructor

        :param plyvel_db:
        :param address: the address of IconScore 
        """
        self._address = address
        super().__init__(db)

    @property
    def address(self):
        return self._address

    def get_from_batch(self,
                       block_batch: BlockBatch,
                       tx_batch: TransactionBatch,
                       key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. BlockBatch
        3. StateDB

        :param key:
        :return: a value for a given key
        """
        # get value from tx_batch
        icon_score_batch = tx_batch[self._address]
        if icon_score_batch:
            value = icon_score_batch.get(key, None)
            if value:
                return value

        # get value from block_batch
        icon_score_batch = block_batch[self._address]
        if icon_score_batch:
            value = icon_score_batch.get(key, None)
            if value:
                return value

        # get value from state_db
        return super().get(key)

    def put_to_batch(self, tx_batch: TransactionBatch, key: bytes, value: bytes):
        tx_batch.put(self._address, key, value)

    def delete(self, key: bytes):
        raise DatabaseException('delete is not allowed')


class InternalScoreDatabase(WritableDatabase):
    """Database for an IconScore only used on the inside of iconservice.

    IconScore can't access this database directly.
    """

    # Thread-local data is data whose values are thread specific
    _thread_local_data = threading.local()

    @property
    def context(self):
        """Returns a different context according to the current thread

        :return: IconScoreContext
        """
        return self._thread_local_data.context

    @context.setter
    def context(self, value: IconScoreContext) -> None:
        self._thread_local_data.context = value

    def get(self, key: bytes) -> bytes:
        """
        """
        value = None
        context = self.context

        if context.readonly:
            value = super().get(key)
        else:
            value = super().get_from_batch(context.block_batch,
                                           context.tx_batch,
                                           key)

        return value

    def put(self, key: bytes, value: bytes):
        context = self.context

        if context.readonly:
            raise DatabaseException('put is not allowed')
        else:
            super().put_to_batch(context.tx_batch, key, value)

        return super().put(key, value)

    def get_sub_db(self, key: bytes):
        """Get Prefixed db

        :param key: (bytes): prefixed_db key
        """

        return InternalScoreDatabase(self._db.prefixed_db(key), self._address)

    def write_batch(self, states: dict):
        context = self.context

        if context.readonly:
            raise DatabaseException('write_batch is not allowed')

        return super().write_batch(states)

    @staticmethod
    def from_address_and_path(
            address: Address,
            path: str,
            create_if_missing=True) -> 'InternalScoreDatabase':
        return InternalScoreDatabase(
            PlyvelDatabase.make_db(path, create_if_missing),
            address)
