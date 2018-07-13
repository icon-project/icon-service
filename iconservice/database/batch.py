# -*- coding: utf-8 -*-

# Copyright 2018 theloop Inc.
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


import hashlib
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..base.block import Block


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
        data = []

        for key, value in self.items():
            data.append(key)
            if value is not None:
                data.append(value)

        return hashlib.sha3_256(b'|'.join(data)).digest()


class TransactionBatch(Batch):
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

    def clear(self):
        self.hash = None
        super().clear()


class BlockBatch(Batch):
    """Contains the states changed by a block

    key: Address
    value: IconScoreBatch
    """
    def __init__(self, block: Optional['Block'] = None):
        """
        """
        super().__init__()
        self.block = block

    def clear(self) -> None:
        self.block = None
        super().clear()
