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

from hashlib import sha3_256
from typing import TYPE_CHECKING

from .deposit import Deposit
from .deposit_meta import DepositMeta
from ..base.ComponentBase import StorageBase
from ..base.address import Address

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    """Fee and Deposit state manager embedding a state db wrapper"""

    _FEE_PREFIX = b'\x02'

    def _generate_key(self, key_data: bytes):
        """
        Generates a db key
        """
        return self._FEE_PREFIX + sha3_256(key_data).digest()

    def get_deposit_meta(self, context: 'IconScoreContext', score_address: 'Address') -> 'DepositMeta':
        """Returns the score deposit meta information.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: DepositMeta object
        """
        key = self._generate_key(score_address.to_bytes())
        value = self._db.get(context, key)
        return DepositMeta.from_bytes(value) if value else None

    def put_deposit_meta(self, context: 'IconScoreContext', score_address: 'Address', deposit_meta: 'DepositMeta'):
        """Puts the score deposit meta information into db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :param deposit_meta: DepositMeta object
        :return: None
        """
        key = self._generate_key(score_address.to_bytes())
        value = deposit_meta.to_bytes()
        self._db.put(context, key, value)

    def delete_deposit_meta(self, context: 'IconScoreContext', score_address: 'Address'):
        """Deletes the score deposit meta information from db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: None
        """
        key = self._generate_key(score_address.to_bytes())
        self._db.delete(context, key)

    def get_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> 'Deposit':
        """Returns the deposit.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: Deposit Object
        """
        key = self._generate_key(deposit_id)
        value = self._db.get(context, key)

        if value:
            value = Deposit.from_bytes(value)
            value.id = deposit_id

        return value

    def put_deposit(self, context: 'IconScoreContext', deposit: 'Deposit'):
        """Puts the deposit data into db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit: Deposit Object
        :return: None
        """
        key = self._generate_key(deposit.id)
        value = deposit.to_bytes()
        self._db.put(context, key, value)

    def delete_deposit(self, context: 'IconScoreContext', deposit_id: bytes):
        """Deletes the deposit from db.

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: None
        """
        key = self._generate_key(deposit_id)
        self._db.delete(context, key)
