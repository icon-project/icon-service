# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base.address import Address


class RewardCalcProxy(object):
    def __init__(self):
        self._loop = None

    def calculate(self, iiss_db_path: str, block_height: int):
        """Request RewardCalculator to calculate IScore for every account

        :param iiss_db_path: the absolute path of iiss database
        :param block_height: The blockHeight when this request are sent to RewardCalculator
        """
        pass

    def claim(self, address: 'Address', block_height: int, block_hash: bytes) -> list:
        """Claim IScore of a given address

        :param address: the address to claim
        :return: [Address, IScore(INT), blockHeight(Uint64)]
        """
        pass

    def query(self, address: 'Address') -> list:
        """Returns the I-Score of a given address

        :param address:
        :return:
        """
        pass

    def commit_block(self, block_height: int, block_hash: bytes) -> list:
        pass

    def rollback_block(self, block_height: int, block_hash: bytes) -> list:
        pass
