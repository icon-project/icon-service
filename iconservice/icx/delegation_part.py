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

from ..utils import toggle_flags
from ..base.exception import InvalidParamsException
from ..icon_constant import IISS_MAX_DELEGATIONS
from ..utils.msgpack_for_db import MsgPackForDB
from .icx_account import PartFlag

if TYPE_CHECKING:
    from ..base.address import Address


class DelegationPart(object):
    _VERSION = 0
    PREFIX = b"aod|"

    def __init__(self, delegated_amount: int = 0, delegations: list = None):
        if delegations:
            self._delegations: list = delegations
        else:
            self._delegations: list = []

        self._delegated_amount: int = delegated_amount
        self._delegations_amount: int = self._update_delegations_amount()
        self._flags: int = PartFlag.NONE

    @staticmethod
    def make_key(address: 'Address'):
        return DelegationPart.PREFIX + address.to_bytes_including_prefix()

    @property
    def delegated_amount(self) -> int:
        return self._delegated_amount

    @property
    def delegations(self) -> list:
        return self._delegations

    @property
    def delegations_amount(self) -> int:
        return self._delegations_amount

    @property
    def flags(self) -> int:
        return self._flags

    def _update_delegations_amount(self) -> int:
        total_delegation_amount: int = 0
        for address, value in self.delegations:
            total_delegation_amount += value
        return total_delegation_amount

    def update_delegated_amount(self, offset: int):
        self._delegated_amount += offset
        self._flags = toggle_flags(self._flags, PartFlag.DELEGATION_DIRTY, True)

    def set_delegations(self, new_delegations: list):
        if len(new_delegations) > IISS_MAX_DELEGATIONS:
            raise InvalidParamsException('overflow delegations')

        self._delegations: list = new_delegations
        self._delegations_amount: int = self._update_delegations_amount()
        self._flags = toggle_flags(self._flags, PartFlag.DELEGATION_DIRTY, True)

    @staticmethod
    def from_bytes(buf: bytes) -> 'DelegationPart':
        """Create DelegationPart object from bytes data

        :param buf: (bytes) bytes data including DelegationPart information
        :return: (DelegationPart) DelegationPart object
        """

        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        assert version == DelegationPart._VERSION

        delegated_amount: int = data[1]
        delegation_list: list = data[2]
        delegations: list = []
        for i in range(0, len(delegation_list), 2):
            item = (delegation_list[i], delegation_list[i + 1])
            delegations.append(item)

        return DelegationPart(delegated_amount=delegated_amount, delegations=delegations)

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of AccountOfDelegation object
        """

        data = [
            self._VERSION,
            self.delegated_amount
        ]
        delegations: list = []
        for address, value in self.delegations:
            delegations.append(address)
            delegations.append(value)
        data.append(delegations)

        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (AccountOfDelegation)
        """

        return isinstance(other, DelegationPart) \
            and self._delegated_amount == other.delegated_amount \
            and self._delegations == other.delegations

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (AccountOfDelegation)
        """
        return not self.__eq__(other)
