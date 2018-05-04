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


from .address import Address


class Transaction(object):
    """Contains transaction info
    """

    def __init__(self,
                 tx_hash: str = None,
                 origin: Address = None,
                 timestamp: int = None,
                 nonce: int = None) -> None:
        """Transaction class for icon score context
        """
        self.__hash = tx_hash
        self.__origin = origin
        self.__timestamp = timestamp
        self.__nonce = nonce

    @property
    def origin(self) -> Address:
        """transaction creator

        :return:
        """
        return self.__origin

    @property
    def index(self) -> int:
        return 0

    @property
    def hash(self) -> str:
        """transaction hash
        """
        return self.__hash

    @property
    def timestamp(self) -> int:
        """timestamp of a transaction request
        This is NOT a block timestamp
        """
        return self.__timestamp

    @property
    def nonce(self) -> int:
        """nonce of a transaction request
        """
        return self.__nonce
