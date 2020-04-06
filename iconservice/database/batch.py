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


from collections import OrderedDict, namedtuple
from collections.abc import MutableMapping
from typing import Optional

from ..base.block import Block
from ..base.exception import DatabaseException, AccessDeniedException
from ..icx import IcxStorage
from ..utils import sha3_256

TransactionBatchValue = namedtuple('TransactionBatchValue', ['value', 'include_state_root_hash'])


def digest(ordered_dict: OrderedDict):
    # items in data MUST be byte-like objects
    data = []

    for key, tx_batch_value in ordered_dict.items():
        if tx_batch_value.include_state_root_hash is True:
            value: bytes = tx_batch_value.value
        else:
            continue
        data.append(key)
        if value is not None:
            data.append(value)
    value: bytes = b'|'.join(data)
    return sha3_256(value)


class Batch(OrderedDict):
    def __init__(self):
        super().__init__()

    def digest(self) -> bytes:
        """Create sha3_256 hash value with included updated states

        How to create a hash value:
        hash_value = sha3_256(b'key0|value0|key1|value1|...)

        case1: value1 is None,
            hash_value = sha3_256(b'key0|value0|key1|key2|value2|...)

        case2: value1 = b''
            hash_value = sha3_256(b'key0|value0|key1||value2|...)

        :return: sha3_256 hash value
        """
        # items in data MUST be byte-like objects
        return digest(self)


class TransactionBatch(MutableMapping):
    """Contains the states changed by a transaction.

    key: Score Address
    value: IconScoreBatch
    """
    def __init__(self, tx_hash: Optional[bytes]=None) -> None:
        """Constructor

        :param tx_hash: tx_hash
        """
        super().__init__()
        self.hash = tx_hash
        self._call_batches = [OrderedDict()]

    def __getitem__(self, item):
        for call_batch in reversed(self._call_batches):
            if item in call_batch:
                return call_batch[item]

        return None

    def __setitem__(self, key, value):
        call_batch: OrderedDict = self._call_batches[-1]
        call_batch[key] = value

    def __delitem__(self, key):
        raise DatabaseException('delete item is not allowed')

    def __contains__(self, item):
        for call_batch in self._call_batches:
            if item in call_batch:
                return True

        return False

    def __iter__(self):
        for call_batch in self._call_batches:
            for key in call_batch:
                yield key

    def __len__(self):
        length = 0

        for call_batch in self._call_batches:
            length += len(call_batch)

        return length

    def enter_call(self):
        self._call_batches.append(OrderedDict())

    def revert_call(self):
        call_batch: OrderedDict = self._call_batches[-1]
        call_batch.clear()

    def leave_call(self):
        call_batch: OrderedDict = self._call_batches.pop()

        if call_batch:
            self._call_batches[-1].update(call_batch)

    def digest(self) -> bytes:
        if len(self._call_batches) != 1:
            raise DatabaseException(f'Wrong call_batch count: {len(self._call_batches)}')

        return digest(self._call_batches[0])

    @property
    def call_count(self) -> int:
        return len(self._call_batches)

    def clear(self):
        self.hash = None
        self._call_batches = [OrderedDict()]


class BlockBatch(Batch):
    """Contains the states changed by a block

    key: Address
    value: IconScoreBatch
    """
    def __init__(self, block: Optional['Block'] = None):
        """Constructor

        :param block: block info
        """
        super().__init__()
        self.block = block

    def __setitem__(self, key, value):
        raise AccessDeniedException("Can not set data on block batch directly.")

    def update(self, tx_batch: 'TransactionBatch', **kwargs):
        for key, value in tx_batch.items():
            super().__setitem__(key, value)

    def update_block_hash(self, block_hash: bytes):
        self.block = Block(block_height=self.block.height,
                           block_hash=block_hash,
                           timestamp=self.block.timestamp,
                           prev_hash=self.block.prev_hash,
                           cumulative_fee=self.block.cumulative_fee)

    def set_block_to_batch(self, revision: int):
        # Logger.debug(tag="DB", msg=f"set_block_to_batch() block={self.block}")
        block_key: bytes = IcxStorage.LAST_BLOCK_KEY
        block_value: tuple = TransactionBatchValue(self.block.to_bytes(revision), False)

        super().__setitem__(block_key, block_value)

    def clear(self) -> None:
        self.block = None
        super().clear()
