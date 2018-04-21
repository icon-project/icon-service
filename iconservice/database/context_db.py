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


def _get_from_batch(batch: dict, key: bytes) -> bytes:
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
    def __init__(self, icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icon_score_info_mapper: To get state db for an icon score
        """
        self._icon_score_address = None
        self._icon_score_info_mapper = icon_score_info_mapper
        self._tx_batch = TransactionBatch()
        self._block_batch = BlockBatch()
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
        assert(self._icon_score_address)

        # get value from tx_batch
        icon_score_batch = self._tx_batch[self._icon_score_address]
        value = _get_from_batch(icon_score_batch, key)
        if value:
            return value

        # get value from block_batch
        icon_score_batch = self._block_batch[self._icon_score_address]
        value = _get_from_batch(icon_score_batch, key)
        if value:
            return value

        # get value from state_db
        return self._score_db.get(key)

    @property
    def icon_score_address(self) -> Address:
        """Returns the address of the icon score
        which possesses this database at this time

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
        assert(self._tx_batch is not None)
        assert(self._icon_score_address)
        self._tx_batch.put(self._icon_score_address, key, value)

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
        """Rollback the changed states for the current transaction
        """
        self._tx_batch.clear()

    def start_block(self, height: int, hash: str) -> None:
        """Begin to change states with a block 
        """
        self._block_batch.clear()
        self._block_batch.height = height
        self._block_batch.hash = hash

    def end_block(self) -> None:
        """End to change states with a block
        """
        # Do nothing

    def commit(self) -> None:
        """Write changed states in a BlockBatch to StateDB
        """
        for icon_score_address in self._block_batch:
            score_db = self._icon_score_info_mapper[icon_score_address].db
            icon_score_batch = self._block_batch[icon_score_address]

            for key in icon_score_batch:
                score_db.put(key, icon_score_batch[key])

        self._block_batch.clear()

    def rollback(self) -> None:
        """Rollback updated states in a BlockBatch
        """
        self._tx_batch.clear()
        self._block_batch.clear()
