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
from .transaction_batch import TransactionBatch
from .icon_score_batch import IconScoreBatch


class BlockBatch(dict):
    """
    key: Address
    value: IconScoreBatch
    """
    def __init__(self, height, hash=None):
        """
        """
        self.__height = height
        self.__hash = hash

    @property
    def height(self):
        return self.__height

    @property
    def hash(self):
        return self.__hash

    def put(self, address: Address, key: object, value: object) -> None:
        """
        :param address: icon_score_address
        :param key: a key of state
        :param value: a value of state
        """
        icon_score_batch = None

        if address in self:
            icon_score_batch = self[address]
        else:
            icon_score_batch = IconScoreBatch(address)
            self[address] = icon_score_batch

        icon_score_batch[key] = value

    def put_tx_batch(self, tx_batch: TransactionBatch) -> None:
        for icon_score_address in tx_batch:
            icon_score_batch = tx_batch[icon_score_address]
            for key in icon_score_batch:
                self.put(icon_score_address, key, icon_score_batch[key])
