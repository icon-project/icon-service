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

from collections import OrderedDict
from typing import TYPE_CHECKING

from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address


class DelegationPart(object):
    _VERSION = 0
    PREFIX = b"aod|"

    def __init__(self, delegated_amount: int = 0, delegations: OrderedDict = None):
        self._delegated_amount: int = delegated_amount
        if delegations:
            self._delegations: OrderedDict = delegations
        else:
            self._delegations: OrderedDict = OrderedDict()

    @staticmethod
    def make_key(address: 'Address'):
        return DelegationPart.PREFIX + address.to_bytes_including_prefix()

    @property
    def delegated_amount(self) -> int:
        return self._delegated_amount

    @delegated_amount.setter
    def delegated_amount(self, delegated_amount: int):
        self._delegated_amount = delegated_amount

    @property
    def delegations(self) -> OrderedDict:
        return self._delegations

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
        delegations: OrderedDict = OrderedDict()
        for i in range(0, len(delegation_list), 2):
            info = DelegationPartInfo()
            info.address = delegation_list[i]
            info.value = delegation_list[i + 1]
            delegations[info.address] = info

        return DelegationPart(delegated_amount=delegated_amount, delegations = delegations)

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of AccountOfDelegation object
        """

        data = [
            self._VERSION,
            self.delegated_amount
        ]
        delegations = []
        for info in self.delegations.values():
            delegations.append(info.address)
            delegations.append(info.value)
        data.append(delegations)

        return MsgPackForDB.dumps(data)

    def delegate(self, to_address: 'Address', to: 'DelegationPart', value: int) -> bool:
        info: 'DelegationPartInfo' = self._delegations.get(to_address)

        if info is None:
            if value == 0:
                ret = False
            else:
                info: 'DelegationPartInfo' = DelegationPart.create_delegation(to_address, value)
                self._delegations[to_address] = info
                to.delegated_amount += value
                ret = True
        else:
            prev_value: int = info.value
            offset: int = value - prev_value

            if offset != 0:
                info.value += offset
                to.delegated_amount += offset
                ret = True
            else:
                ret = False

            if info.value == 0:
                del self._delegations[info.address]
        return ret

    # def func(self):
    #     if not isinstance(delegations, list):
    #         raise InvalidParamsException('Failed to delegation: delegations is not list type')
    #
    #     if len(delegations) > IISS_MAX_DELEGATION_LIST:
    #         raise InvalidParamsException(f'Failed to delegation: Overflow Max Input List')
    #
    #     from_account: 'Account' = cls.icx_storage.get_account(context, from_address, AccountType.STAKE_DELEGATION)
    #     stake: int = from_account.stake
    #
    #     total_amoount: int = 0
    #     update_list: dict = {}
    #
    #     prev_delegations = deepcopy(from_account.delegations)
    #     for address in prev_delegations:
    #         target_account: 'Account' = cls.icx_storage.get_account(context, address, AccountType.DELEGATION)
    #
    #         if target_account.address == from_account.address:
    #             target_account = from_account
    #
    #         if from_account.delegate(target_account, 0):
    #             update_list[address] = target_account
    #
    #     for delegation in delegations:
    #         address: 'Address' = delegation[ConstantKeys.ADDRESS]
    #         value: int = delegation[ConstantKeys.VALUE]
    # 
    #         target_account: 'Account' = cls.icx_storage.get_account(context, address, AccountType.DELEGATION)
    #
    #         if target_account.address == from_account.address:
    #             target_account = from_account
    #
    #         if from_account.delegate(target_account, value):
    #             update_list[address] = target_account
    #         total_amoount += value
    #
    #     if len(from_account.delegations) > IISS_MAX_DELEGATION_LIST:
    #         raise InvalidParamsException(f'Failed to delegation: Overflow Max Account List')
    #
    #     if stake < total_amoount:
    #         raise InvalidParamsException('Failed to delegation: stake < total_delegations')
    #
    #     cls.icx_storage.put_account(context, from_account, AccountType.STAKE_DELEGATION)
    #
    #     for address, account in update_list.items():
    #         if address == from_account.address:
    #             continue
    #
    #         cls.icx_storage.put_account(context, account, AccountType.DELEGATION)
    #
    #     # TODO tx_result make if needs

    @staticmethod
    def create_delegation(address: 'Address', value: int) -> 'DelegationPartInfo':
        d = DelegationPartInfo()
        d.address: 'Address' = address
        d.value: int = value
        return d

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


class DelegationPartInfo(object):
    def __init__(self):
        self.address: 'Address' = None
        self.value: int = 0

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (AccountDelegationInfo)
        """
        return isinstance(other, DelegationPartInfo) \
            and self.address == other.address \
            and self.value == other.value

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (AccountDelegationInfo)
        """
        return not self.__eq__(other)

    def to_dict(self):
        return {
            "address": self.address,
            "value": self.value
        }
