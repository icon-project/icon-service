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
from .icon_score_batch import IconScoreBatch


class TransactionBatch(object):
    """
    """
    def __init__(self, hash: str) -> None:
        """
        """
        self.__hash = hash
        self.__icon_score_batches = {}

    @property
    def hash(self) -> str:
        """
        """
        return self.__hash

    def get(self, address: Address) -> IconScoreBatch:
        """
        """
        return self.__icon_score_batches.get(address, None)

    def put(self, address: Address, key: bytes, value: bytes):
        """
        """
        icon_score_batch = None

        if address in self.__icon_score_batches:
            icon_score_batch = self.__icon_score_batches[address]
        else:
            icon_score_batch = IconScoreBatch(address)
            self.__icon_score_batches[address] = icon_score_batch

        icon_score_batch.put(key, value)
