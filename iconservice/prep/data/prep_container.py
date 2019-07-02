# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from typing import List, Optional

from iconcommons import Logger

from .prep import PRep, PRepFlag, PRepStatus
from .sorted_list import SortedList
from ...base.address import Address
from ...base.exception import InvalidParamsException, AccessDeniedException
from ...iconscore.icon_score_context import IconScoreContext


class PRepContainer(object):
    """Contains PRep objects

    P-Rep PRep object contains information on registration and delegation.
    PRep objects are sorted in descending order by delegated amount.
    """

    def __init__(self, flags: PRepFlag = PRepFlag.NONE, total_prep_delegated: int = 0):
        self._flags: 'PRepFlag' = flags
        # Total amount of delegated which all active P-Reps have
        self._total_prep_delegated: int = total_prep_delegated
        self._active_prep_dict = {}
        self._active_prep_list = SortedList()
        self._inactive_prep_dict = {}

    def is_frozen(self) -> bool:
        return bool(self._flags & PRepFlag.FROZEN)

    def is_flag_on(self, flags: 'PRepFlag') -> bool:
        return (self._flags & flags) == flags

    @property
    def total_prep_delegated(self) -> int:
        """Returns total amount of delegated which all active P-Reps have

        :return:
        """
        assert self._total_prep_delegated >= 0
        return self._total_prep_delegated

    def load(self, context: 'IconScoreContext'):
        """Load active and inactive P-Rep list from StateDB on startup

        :param context:
        :return:
        """
        for prep in context.storage.prep.get_prep_iterator():
            if prep.status == PRepStatus.ACTIVE:
                self._active_prep_dict[prep.address] = prep
                self._active_prep_list.add(prep)

                self._total_prep_delegated += prep.delegated
                assert self._total_prep_delegated >= 0
            else:
                self._inactive_prep_dict[prep.address] = prep

            prep.freeze()

        self._flags |= PRepFlag.FROZEN

    def freeze(self):
        """Freeze data in PRepContainer
        Freezing makes all data in PRepContainer immutable

        :return:
        """
        if self.is_frozen():
            return

        self._flags |= PRepFlag.FROZEN

        for prep in self._active_prep_list:
            prep.freeze()

    def add(self, prep: 'PRep'):
        """Add a new active P-Rep through registerPRep JSON-RPC API

        It is not allowed to a P-Rep which has been already registered

        :param prep: prep to add
        """
        assert prep.status == PRepStatus.ACTIVE

        self._check_access_permission()

        if prep.address in self:
            raise InvalidParamsException(f"P-Rep already exists: {str(prep.address)}")

        self._active_prep_dict[prep.address] = prep
        self._active_prep_list.add(prep)

        # Update self._total_prep_delegated
        self._total_prep_delegated += prep.delegated
        assert self._total_prep_delegated >= 0

        self._flags |= PRepFlag.DIRTY

        assert len(self._active_prep_dict) == len(self._active_prep_list)

    def remove(self,
               address: 'Address',
               status: 'PRepStatus' = PRepStatus.UNREGISTERED) -> Optional['PRep']:
        """Remove a prep

        * Remove a prep from active_prep_dict and active_prep_list
        * Add a prep to inactive_prep_dict

        :param address:
        :param status:
        :return:
        """
        assert status != PRepStatus.ACTIVE

        self._check_access_permission()

        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None:
            raise InvalidParamsException("P-Rep not found")

        self._active_prep_list.remove(prep)
        del self._active_prep_dict[address]
        assert len(self._active_prep_dict) == len(self._active_prep_list)

        prep.status = status
        self._inactive_prep_dict[address] = prep

        self._total_prep_delegated -= prep.delegated
        assert self._total_prep_delegated >= 0

        return prep

    def set_delegated_to_prep(self, address: 'Address', delegated: int):
        """Update the delegated amount of P-Rep, sorting the P-Rep in ascending order by prep.order()

        :param address: P-Rep address
        :param delegated:
        :return:
        """
        assert delegated >= 0
        self._check_access_permission()

        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None:
            # It is possible to delegate to address which is not a P-Rep
            Logger.info(tag="PREP", msg=f"P-Rep not found: {str(address)}")
            return

        # Remove old prep from self._active_prep_list
        self._active_prep_list.remove(prep)

        if prep.is_frozen():
            prep: 'PRep' = prep.copy(PRepFlag.NONE)
            self._active_prep_dict[address] = prep

        self._total_prep_delegated += delegated - prep.delegated
        assert self._total_prep_delegated >= 0

        prep.delegated = delegated

        self._active_prep_list.add(prep)

    def __contains__(self, address: 'Address') -> bool:
        """Check whether the active P-Rep which has a given address are contained

        :param address:
        :return:
        """
        if not isinstance(address, Address):
            raise InvalidParamsException

        return address in self._active_prep_dict

    def contains(self, address: 'Address', inactive_preps_included: bool = True) -> bool:
        """Check whether the P-Rep is contained regardless of its PRepStatus

        :param address: Address
        :param inactive_preps_included: bool
        :return: True(contained) False(not contained)
        """
        return \
            address in self._active_prep_dict \
            or (inactive_preps_included and address in self._inactive_prep_dict)

    def __iter__(self):
        """Active P-Rep iterator

        :return:
        """
        for prep in self._active_prep_list:
            yield prep

    def get_by_index(self, index: int, mutable: bool = False) -> Optional['PRep']:
        """Returns an active P-Rep with a given index

        :param index:
        :param mutable:
        :return:
        """
        prep: 'PRep' = self._active_prep_list.get(index)
        if not mutable:
            return prep

        self._check_access_permission()

        return self._get_mutable_prep(index, prep)

    def get_by_address(self, address: 'Address', mutable: bool = False) -> Optional['PRep']:
        """Returns an active P-Rep with a given address

        :param address: The address of a P-Rep
        :param mutable: True(prep to return should be mutable)
        :return: The instance of a PRep which has a given address
        """
        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None or not mutable:
            return prep

        self._check_access_permission()
        index: int = self._active_prep_list.index(prep)

        return self._get_mutable_prep(index, prep)

    def _get_mutable_prep(self, index: int, prep: 'PRep') -> Optional['PRep']:
        if prep is None:
            return None

        if prep.is_frozen():
            prep: 'PRep' = prep.copy(PRepFlag.NONE)
            self._active_prep_dict[prep.address] = prep
            self._active_prep_list[index] = prep

        return prep

    def __len__(self) -> int:
        """Returns the number of active P-Reps

        :return: the number of active P-Reps
        """
        assert len(self._active_prep_list) == len(self._active_prep_dict)
        return len(self._active_prep_list)

    def get_preps(self, start_index: int, size: int) -> List['PRep']:
        """Returns

        :return: P-Rep list
        """
        return self._active_prep_list[start_index:start_index + size]

    def index(self, address: 'Address') -> int:
        """Returns the index of a given address in active_prep_list

        :return: zero-based index
        """
        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None:
            Logger.info(tag="PREP", msg=f"P-Rep not found: {str(address)}")
            return -1

        index: int = self._active_prep_list.index(prep)
        assert index >= 0

        return index

    def copy(self, mutable: bool) -> 'PRepContainer':
        """Copy PRepContainer without changing PRep objects

        :param mutable:
        :return:
        """
        flags: 'PRepFlag' = PRepFlag.NONE if mutable else PRepFlag.FROZEN
        preps = PRepContainer(flags, self._total_prep_delegated)

        preps._active_prep_dict.update(self._active_prep_dict)
        preps._active_prep_list.extend(self._active_prep_list)
        preps._inactive_prep_dict.update(self._inactive_prep_dict)

        return preps

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("PRepContainer access denied")
