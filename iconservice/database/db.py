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

from iconservice.base.address import Address
from iconservice.base.exception import DatabaseException
from iconservice.database.batch import BlockBatch, TransactionBatch


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

    @property
    # @abc.abstractmethod
    def address(self):
        return None


class PlyvelDatabase(IconServiceDatabase):
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
        self.__db = db

    def get(self, key: bytes) -> bytes:
        """Get value from db using key

        :param key: db key
        :return: value indicated by key otherwise None
        """
        return self.__db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """Put value into db using key.

        :param key: (bytes): db key
        :param value: (bytes): db에 저장할 데이터
        """
        self.__db.put(key, value)

    def delete(self, key: bytes) -> None:
        """Delete a row

        :param key: delete the row indicated by key.
        """
        self.__db.delete(key)

    def close(self) -> None:
        """Close db
        """
        if self.__db:
            self.__db.close()
            self.__db = None

    def get_sub_db(self, key: bytes) -> IconServiceDatabase:
        """Get Prefixed db

        :param key: (bytes): prefixed_db key
        """

        return PlyvelDatabase(self.__db.prefixed_db(key))

    def iterator(self) -> iter:
        return self.__db.iterator()

    def write_batch(self, states: dict) -> None:
        """bulk data modification

        :param states: key:value pairs
            key and value should be bytes type
        """
        if states is None or len(states) == 0:
            return

        with self.__db.write_batch() as wb:
            for key in states:
                wb.put(key, states[key])


class ReadOnlyDatabase(IconServiceDatabase):
    def __init__(self, db: PlyvelDatabase):
        self.__db = db

    def get(self, key: bytes) -> bytes:
        return self.__db.get(key)

    def put(self, key: bytes, value: bytes):
        raise DatabaseException('put is not allowed')

    def delete(self, key: bytes):
        raise DatabaseException('delete is not allowed')

    def close(self):
        raise DatabaseException('close is not allowed')

    def get_sub_db(self, key: bytes):
        return self.__db.get_sub_db(key)

    def iterator(self):
        return self.__db.iterator()

    def write_batch(self, states: dict):
        raise DatabaseException('write_batch is not allowed')


class WritableDatabase(IconServiceDatabase):
    """Cache + LevelDB
    """

    def __init__(self,
                 address: Address,
                 db: PlyvelDatabase,
                 block_batch: BlockBatch,
                 tx_batch: TransactionBatch) -> None:
        """Constructor

        :param address: the address of iconscore 
        :param db: db object is shared with ReadOnlyDatabase
        :param block_batch:
        :param tx_batch:
        """
        self.__address = address
        self.__db = db

        # two batch objects are managed in outside
        self.__block_batch = block_batch
        self.__tx_batch = tx_batch

    def get(self, key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. BlockBatch
        3. StateDB

        :param key:
        :return: a value for a given key
        """
        # get value from tx_batch
        icon_score_batch = self.__tx_batch[self.__address]
        if icon_score_batch:
            return icon_score_batch.get(key, None)

        # get value from block_batch
        icon_score_batch = self.__block_batch[self.__address]
        if icon_score_batch:
            return icon_score_batch.get(key, None)

        # get value from state_db
        return self.__db.get(key)

    def put(self, key: bytes, value: bytes):
        self.__tx_batch.put(self.__address, key, value)

    def delete(self, key: bytes):
        raise DatabaseException('delete is not allowed')

    def close(self):
        self.__db.close()

    def get_sub_db(self, key: bytes):
        return self.__db.get_sub_db(key)

    def iterator(self):
        return self.__db.iterator()

    def write_batch(self, states: dict):
        self.__db.write_batch(states)
