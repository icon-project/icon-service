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
import hashlib
import plyvel
import threading

from iconservice.base.address import Address
from iconservice.base.exception import DatabaseException
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.utils import sha3_256


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


class ContextDatabase(PlyvelDatabase):
    """Database for an IconScore only used on the inside of iconservice.

    IconScore can't access this database directly.
    Cache + LevelDB
    """

    def __init__(self,
                 db: plyvel.DB,
                 address: Address) -> None:
        """Constructor

        :param plyvel_db:
        :param address: the address of IconScore 
        """
        super().__init__(db)
        self.address = address

    def get(self, context: IconScoreContext, key: bytes) -> bytes:
        """
        """
        value = None

        if context.readonly \
                or context.type == IconScoreContextType.GENESIS:
            value = super().get(key)
        else:
            value = self.get_from_batch(context, key)

        return value

    def get_from_batch(self,
                       context: IconScoreContext,
                       key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. BlockBatch
        3. StateDB

        :param key:
        :return: a value for a given key
        """
        block_batch = context.block_batch
        tx_batch = context.tx_batch

        # get value from tx_batch
        icon_score_batch = tx_batch[self.address]
        if icon_score_batch:
            value = icon_score_batch.get(key, None)
            if value:
                return value

        # get value from block_batch
        icon_score_batch = block_batch[self.address]
        if icon_score_batch:
            value = icon_score_batch.get(key, None)
            if value:
                return value

        # get value from state_db
        return super().get(key)

    def put(self,
            context: IconScoreContext,
            key: bytes,
            value: bytes) -> None:
        """
        """
        if context.readonly:
            raise DatabaseException('put is not allowed')
        elif context.type == IconScoreContextType.INVOKE:
            self.put_to_batch(context, key, value)
        else:
            super().put(key, value)

    def put_to_batch(self, context: IconScoreContext, key: bytes, value: bytes):
        context.tx_batch.put(self.address, key, value)

    def delete(self, context: IconScoreContext, key: bytes):
        if context.readonly:
            raise DatabaseException('delete is not allowed')
        else:
            super().delete(key)

    def write_batch(self,
                    context: IconScoreContext,
                    states: dict):
        if context.readonly:
            raise DatabaseException(
                'write_batch is not allowed on readonly context')

        return super().write_batch(states)

    @staticmethod
    def from_address_and_path(
            address: Address,
            path: str,
            create_if_missing=True) -> 'ContextDatabase':
        return ContextDatabase(
            PlyvelDatabase.make_db(path, create_if_missing),
            address)


class ScoreDatabase(object):
    """It is used in IconScore

    IconScore developer will get and use ScoreDatabase instance in IconScore
    """
    def __init__(self, icon_score: 'IconScoreBase', prefix: bytes=b'') -> None:
        """
        """
        self.__prefix = prefix
        self.__icon_score = icon_score

    def get(self, key: bytes) -> bytes:
        key = self.__hash_key(key)
        return self.__icon_score.get_from_db(key)

    def put(self, key: bytes, value: bytes):
        key = self.__hash_key(key)
        self.__icon_score.put_to_db(key, value)

    def get_sub_db(self, prefix: bytes) -> 'ScoreDatabase':
        return ScoreDatabase(self.__icon_score, prefix)

    def delete(self, key: bytes):
        key = self.__hash_key(key)
        self.__icon_score.delete_from_db(key)

    def __hash_key(self, key: bytes):
        key = sha3_256(self.__prefix + key)
