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


from ..base.address import Address
from ..iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .batch import BlockBatch, TransactionBatch


def __get_from_batch(key: bytes, batch: dict) -> bytes:
    """
    """
    if batch:
        return batch.get(key, None)
    else:
        return None


class ReadOnlyContextDatabase(object):
    """ReadonlyDatabase used by IconScore

    DB writing is not allowed.
    """
    def __init__(self,
                 icon_score_address: Address,
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icon_score_address: the current icon score address
        :param icon_score_info_mapper: To get state db for an icon score
        """
        self.icon_score_address = icon_score_address
        self.__icon_score_info_mapper = icon_score_info_mapper

    def get(self, key: bytes) -> bytes:
        """Returns a value for the given key

        :param key:
        :return:
        """
        info = self.__icon_score_info_mapper[self.icon_score_address]
        return info.db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """DB writing is not allowed on readonly mode.

        :param key:
        :param value:
        """
        raise RuntimeError('Updating state is not allowed')


class ContextDatabase(object):
    """Database used by IconScore

    This db will be provided to IconScore made by 3-party
    through a IconScoreContext
    """
    def __init__(self,
                 icon_score_address: Address,
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icon_score_address: the current icon score address
        :param icon_score_info_mapper: To get state db for an icon score
        """
        self._icon_score_address = icon_score_address
        self._icon_score_info_mapper = icon_score_info_mapper

        self._tx_batch = TransactionBatch()
        self._block_batch = None
        self._score_db = None

    def get(self, key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. BlockBatch
        3. ScoreDB

        :param key:
        :return: a value for a given key
        """
        value = __get_from_batch(key, self._tx_batch)
        if value is None:
            value = __get_from_batch(key, self._block_batch)
            if value is None:
                value = self._score_db.get(key)

        return value

    @property
    def icon_score_address(self) -> Address:
        """Returns the address of the current icon score which uses this database now

        "return: icon_score_address
        """
        return self._icon_score_address

    @icon_score_address.setter
    def icon_score_address(self, icon_score_address: Address) -> None:
        """Set the address of the icon score

        :param address: icon_score_address
        """
        self._icon_score_address = icon_score_address
        self._score_db = self._icon_score_info_mapper[icon_score_address].db

    def put(self, key: bytes, value: bytes) -> None:
        """Update a new state to TransactionBatch
        """
        assert(self._tx_batch)
        self._tx_batch[key] = value

    def start_transaction(self, tx_hash: str) -> None:
        """Begin to update states for a transaction
        """
        self._tx_batch.hash = tx_hash

    def end_transaction(self) -> None:
        """Finish updating states for a transaction
        """
        self._block_batch.put_tx_batch(self._tx_batch)
        self._tx_batch.clear()

    def rollback_transaction(self) -> None:
        """Rollback the current states for the current transaction
        """
        self._tx_batch.clear()

    def commit(self) -> None:
        """Write updated states in a BlockBatch to StateDB
        """
        for icon_score_batch in self._block_batch:
            address = icon_score_batch.address
            score_db = self._icon_score_info_mapper[address].db

            for key in icon_score_batch:
                score_db.put(key, icon_score_batch[key])

    def rollback(self) -> None:
        """Remove updated states in a BlockBatch
        """
        self._tx_batch.clear()
        self._block_batch.clear()
