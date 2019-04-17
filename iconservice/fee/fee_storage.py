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
from hashlib import sha3_256

from .deposit import Deposit
from .score_deposit_info import ScoreDepositInfo
from ..base.address import Address

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


class FeeStorage(object):
    """Fee and Deposit state manager embedding a state db wrapper"""

    _FEE_PREFIX = b'\x02'

    def __init__(self, db: 'ContextDatabase') -> None:
        """Constructor

        :param db: (Database) state db wrapper
        """
        self._db = db

    @property
    def db(self) -> 'ContextDatabase':
        """Returns state db wrapper.

        :return: (Database) state db wrapper
        """
        return self._db

    def get_score_deposit_info(self, context: 'IconScoreContext', score_address: 'Address') -> 'ScoreDepositInfo':
        """Returns the score deposit information.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: ScoreDepositInfo object
        """
        key = self._FEE_PREFIX + sha3_256(score_address.to_bytes()).digest()
        value = self._db.get(context, key)
        return ScoreDepositInfo.from_bytes(value) if value else value

    def put_score_deposit_info(self, context: 'IconScoreContext', score_address: 'Address',
                               score_deposit_info: 'ScoreDepositInfo') -> None:
        """Puts the score deposit information into db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :param score_deposit_info: ScoreDepositInfo object
        :return: None
        """
        key = self._FEE_PREFIX + sha3_256(score_address.to_bytes()).digest()
        value = score_deposit_info.to_bytes()
        self._db.put(context, key, value)

    def delete_score_deposit_info(self, context: 'IconScoreContext', score_address: 'Address') -> None:
        """Deletes the score deposit information from db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: None
        """
        key = self._FEE_PREFIX + sha3_256(score_address.to_bytes()).digest()
        self._db.delete(context, key)

    def get_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> 'Deposit':
        """Returns the deposit.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: Deposit Object
        """
        key = self._FEE_PREFIX + sha3_256(deposit_id).digest()
        value = self._db.get(context, key)

        if value:
            value = Deposit.from_bytes(value)
            value.id = deposit_id

        return value

    def put_deposit(self, context: 'IconScoreContext', deposit_id: bytes, deposit: 'Deposit') -> None:
        """Puts the deposit data into db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :param deposit: Deposit Object
        :return: None
        """
        key = self._FEE_PREFIX + sha3_256(deposit_id).digest()
        value = deposit.to_bytes()
        self._db.put(context, key, value)

    def delete_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> None:
        """Deletes the deposit from db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: None
        """
        key = self._FEE_PREFIX + sha3_256(deposit_id).digest()
        self._db.delete(context, key)

    def close(self,
              context: 'IconScoreContext') -> None:
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None
