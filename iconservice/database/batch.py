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
from typing import Optional


class IconScoreBatch(dict):
    """Contains precommit states for an icon score

    key: state key
    value: state value
    """
    def __init__(self, address: 'Address') -> None:
        """Constructor

        :param address: icon_score_address
        """
        super().__init__()
        self._address = address

    @property
    def address(self) -> 'Address':
        """icon_score_address
        """
        return self._address


class TransactionBatch(dict):
    """Contains the states changed by a transaction.

    key: Score Address
    value: IconScoreBatch
    """
    def __init__(self, tx_hash: str=None) -> None:
        """Constructor

        :param tx_hash: tx_hash
        """
        super().__init__()
        self.hash = tx_hash

    def put(self, address: 'Address', key: bytes, value: bytes) -> None:
        """
        :param address: icon_score_address
        :param key: a key of state
        :param value: a value of state
        """

        if address in self: icon_score_batch = self[address]
        else:
            icon_score_batch = IconScoreBatch(address)
            self[address] = icon_score_batch

        icon_score_batch[key] = value

    def __getitem__(self, key: 'Address') -> Optional['IconScoreBatch']:
        """Get IconScoreBatch instance indicated by address

        :param key: icon_score_address
        """
        if key in self:
            return super().__getitem__(key)
        else:
            return None

    def __setitem__(self,
                    key: Address,
                    value: IconScoreBatch) -> None:
        """operator[] overriding

        :param key: icon_score_address
        :param value: IconScoreBatch object
        """
        if not isinstance(key, Address):
            raise ValueError('key is not Address type')
        if not isinstance(value, IconScoreBatch):
            raise ValueError('value is not IconScoreBatch type')

        super().__setitem__(key, value)

    def clear(self):
        self.hash = None
        super().clear()


class BlockBatch(dict):
    """Contains the states changed by a block

    key: Address
    value: IconScoreBatch
    """
    def __init__(self, block: Optional['Block'] = None):
        """
        """
        super().__init__()
        self.block = block

    def put(self, address: 'Address', key: bytes, value: bytes) -> None:
        """
        :param address: icon_score_address
        :param key: a key of state
        :param value: a value of state
        """

        if address in self:
            icon_score_batch = self[address]
        else:
            icon_score_batch = IconScoreBatch(address)
            self[address] = icon_score_batch

        icon_score_batch[key] = value

    def put_tx_batch(self, tx_batch: 'TransactionBatch') -> None:
        """Put the states of tx_batch

        :param tx_batch:
        """
        for icon_score_address in tx_batch:
            assert(isinstance(icon_score_address, Address))
            icon_score_batch = tx_batch[icon_score_address]

            for key in icon_score_batch:
                value = icon_score_batch[key]
                self.put(icon_score_address, key, value)

    def __getitem__(self, key: 'Address') -> Optional['IconScoreBatch']:
        """Get IconScoreBatch object indicated by address

        :param key: icon_score_address
        """
        if key in self:
            return super().__getitem__(key)
        else:
            return None

    def clear(self):
        self.height = -1
        self.hash = None
        super().clear()
