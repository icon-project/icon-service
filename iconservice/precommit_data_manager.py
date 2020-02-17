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

from threading import Lock
from typing import TYPE_CHECKING, Optional, List

from .base.block import Block, EMPTY_BLOCK
from .base.exception import InvalidParamsException
from .database.batch import BlockBatch
from .database.batch import TransactionBatchValue
from .icon_constant import Revision
from .iconscore.icon_score_mapper import IconScoreMapper
from .iiss.reward_calc.msg_data import TxData
from .system.value import SystemValue
from .utils import bytes_to_hex, sha3_256

if TYPE_CHECKING:
    from .base.address import Address
    from .prep.data import PRepContainer, Term


def _print_block_batch(block_batch: 'BlockBatch') -> List[str]:
    """Print the latest updated states stored in IconServiceEngine
    :return:
    """
    lines = []

    try:
        for i, key in enumerate(block_batch):
            value = block_batch[key]

            if isinstance(value, TransactionBatchValue):
                lines.append(f"{i}: {key.hex()} - {bytes_to_hex(value.value)} - {value.include_state_root_hash}")
            else:
                lines.append(f"{i}: {key.hex()} - {bytes_to_hex(value)}")
    except:
        pass

    return lines


def _print_rc_block_batch(rc_block_batch: list) -> List[str]:
    lines = []

    try:
        tx_index = 0
        for i, data in enumerate(rc_block_batch):
            if isinstance(data, TxData):
                key: bytes = data.make_key(tx_index)
                tx_index += 1
            else:
                key: bytes = data.make_key()

            value: bytes = data.make_value()
            lines.append(f"{i}: {key.hex()} - {value.hex()}")
    except:
        pass

    return lines


class PrecommitData(object):
    def __init__(self,
                 revision: int,
                 rc_db_revision: int,
                 system_value: 'SystemValue',
                 block_batch: 'BlockBatch',
                 block_result: list,
                 rc_block_batch: list,
                 preps: 'PRepContainer',
                 term: Optional['Term'],
                 prev_block_generator: Optional['Address'],
                 prev_block_validators: Optional[List['Address']],
                 score_mapper: Optional['IconScoreMapper'],
                 rc_state_root_hash: Optional[bytes],
                 added_transactions: dict,
                 main_prep_as_dict: Optional[dict]):
        """

        :param block_batch: changed states for a block
        :param block_result: tx_results made from transactions in a block
        :param score_mapper: newly deployed scores in a block

        """
        self.system_value: 'SystemValue' = system_value
        # Todo: check if remove the revision
        self.revision: int = revision
        self.rc_db_revision: int = rc_db_revision
        self.block_batch = block_batch
        self.block_result = block_result
        self.rc_block_batch = rc_block_batch
        # Snapshot of preps
        self.preps = preps
        self.term = term
        self.prev_block_generator = prev_block_generator
        self.prev_block_validators = prev_block_validators
        self.score_mapper = score_mapper
        
        self.is_state_root_hash: bytes = self.block_batch.digest()
        self.rc_state_root_hash: Optional[bytes] = rc_state_root_hash

        self.state_root_hash: bytes = self._make_state_root_hash()

        self.added_transactions: dict = added_transactions
        self.main_prep_as_dict: Optional[dict] = main_prep_as_dict

        # To prevent redundant precommit data logging
        self.already_exists = False

        # Make preps and term immutable
        if preps:
            preps.freeze()
        if term:
            term.freeze()

    def __str__(self):
        lines = [
            f"revision: {self.revision}",
            f"block: {self.block}",
            f"is_state_root_hash: {bytes_to_hex(self.is_state_root_hash)}",
            f"rc_state_root_hash: {bytes_to_hex(self.rc_state_root_hash)}",
            f"state_root_hash: {bytes_to_hex(self.state_root_hash)}",
            f"prev_block_generator: {self.prev_block_generator}",
            "",
            f"added_transactions: {self.added_transactions}",
            f"main_prep_as_dict: {self.main_prep_as_dict}",
            "",
            "block_batch",
        ]

        lines.extend(_print_block_batch(self.block_batch))

        lines.append("")
        lines.append("rc_block_batch")
        lines.extend(_print_rc_block_batch(self.rc_block_batch))

        return "\n".join(lines)

    @property
    def block(self) -> Optional['Block']:
        return None if self.block_batch is None else self.block_batch.block

    def _make_state_root_hash(self) -> bytes:
        if self.revision < Revision.DECENTRALIZATION.value or self.rc_state_root_hash is None:
            return self.is_state_root_hash

        data = [self.is_state_root_hash, self.rc_state_root_hash]
        value: bytes = b'|'.join(data)
        return sha3_256(value)


class PrecommitDataManager(object):
    """Manages multiple precommit block data

    """

    def __init__(self):
        self._lock = Lock()
        self._precommit_data_mapper = {}
        self._last_block: Optional['Block'] = None

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
            self._last_block = block if block else EMPTY_BLOCK

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

    def remove_precommit_state(self, instant_block_hash: bytes):
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
        if not self._is_last_block_valid():
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
                f'No precommit data: block_hash({bytes_to_hex(instant_block_hash)})')

        if not self._is_last_block_valid():
            return

        precommit_block = precommit_data.block

        if self._last_block.hash != precommit_block.prev_hash or \
                self._last_block.height + 1 != precommit_block.height:
            raise InvalidParamsException(
                f'Invalid precommit block: last_block({self._last_block}) precommit_block({precommit_block})')

    def _is_last_block_valid(self) -> bool:
        return self._last_block.height >= 0
