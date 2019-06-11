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
from enum import IntFlag
from threading import Lock
from typing import Optional

from .base.block import Block
from .base.exception import InvalidParamsException
from .database.batch import BlockBatch
from .iconscore.icon_score_mapper import IconScoreMapper


class PrecommitFlag(IntFlag):
    # Empty
    NONE = 0x0
    # Set when STEP price changed on the block
    STEP_PRICE_CHANGED = 0x10
    # Set when STEP costs changed on the block
    STEP_COST_CHANGED = 0x20
    # Set when Max STEP limits changed on the block
    STEP_MAX_LIMIT_CHANGED = 0x40
    # STEP changed flag mask
    STEP_ALL_CHANGED = 0xf0


class PrecommitData(object):
    def __init__(self,
                 block_batch: 'BlockBatch',
                 block_result: list,
                 score_mapper: Optional['IconScoreMapper']=None,
                 precommit_flag: PrecommitFlag = PrecommitFlag.NONE):
        """

        :param block_batch: changed states for a block
        :param block_result: tx_results made from transactions in a block
        :param score_mapper: newly deployed scores in a block
        :param precommit_flag: precommit flag

        """
        self.block_batch = block_batch
        self.block_result = block_result
        self.score_mapper = score_mapper
        self.precommit_flag = precommit_flag
        self.block = block_batch.block
        self.state_root_hash: bytes = self.block_batch.digest()


class PrecommitDataManager(object):
    """Manages multiple precommit data made from next candidate block

    """

    def __init__(self):
        self._lock = Lock()
        self._precommit_data_mapper = {}
        self._last_block: 'Block' = None

    @property
    def last_block(self) -> 'Block':
        with self._lock:
            return self._last_block

    @last_block.setter
    def last_block(self, block: 'Block'):
        """Set the last confirmed block

        :param block:
        :return:
        """
        with self._lock:
            self._last_block = block

    def push(self, precommit_data: 'PrecommitData'):
        block: 'Block' = precommit_data.block_batch.block
        self._precommit_data_mapper[block.hash] = precommit_data

    def get(self, block_hash: 'bytes') -> Optional['PrecommitData']:
        precommit_data = self._precommit_data_mapper.get(block_hash)
        return precommit_data

    def commit(self, block: 'Block'):
        with self._lock:
            self._last_block = block

        # Clear remaining precommit data which have the same block height
        self._precommit_data_mapper.clear()

    def rollback(self, instant_block_hash: bytes):
        if instant_block_hash in self._precommit_data_mapper:
            del self._precommit_data_mapper[instant_block_hash]

    def empty(self) -> bool:
        return len(self._precommit_data_mapper) == 0

    def clear(self):
        """Clear precommit data

        :return:
        """
        self._precommit_data_mapper.clear()

    def validate_block_to_invoke(self, block: 'Block'):
        """Check if the block to invoke is valid before invoking it

        :param block: block to invoke
        """
        if self._last_block is None:
            return

        if block.prev_hash == self._last_block.hash and \
                block.height == self._last_block.height + 1:
            return

        raise InvalidParamsException(
            f'Failed to invoke a block: '
            f'last_block({self._last_block}) '
            f'block_to_invoke({block})')

    def validate_precommit_block(self, instant_block_hash: bytes):
        """Check block validation
        before write_precommit_state() or remove_precommit_state()

        :param instant_block_hash: hash data which is used for retrieving block instance from the pre-commit data mapper
        """
        assert isinstance(instant_block_hash, bytes)

        precommit_data = self._precommit_data_mapper.get(instant_block_hash)
        if precommit_data is None:
            raise InvalidParamsException(
                f'No precommit data: block hash: ({instant_block_hash})')

        if self._last_block is None:
            return

        precommit_block = precommit_data.block

        if self._last_block.hash != precommit_block.prev_hash or \
                self._last_block.height + 1 != precommit_block.height:
            raise InvalidParamsException(
                f'Invalid precommit block: last_block({self._last_block}) precommit_block({precommit_block})')
