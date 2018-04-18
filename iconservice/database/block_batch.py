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


from .transaction_batch import TransactionBatch

class BlockBatch(object):
    """
    """
    def __init__(self, height, hash=None):
        """
        """
        self.__height = height
        self.__hash = hash
        self.__icon_score_batches = {}

    @property
    def block_height(self):
        return self.__height

    @property
    def hash(self):
        return self.__hash

    def get(self, address: Address, key: bytes, value: bytes) -> bytes:

    def merge(self, tx_batch: TransactionBatch) -> None:
