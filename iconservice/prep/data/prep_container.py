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
from ...utils import toggle_flags


class PRepContainer(object):
    """Contains PRep objects

    P-Rep PRep object contains information on registration and delegation.
    PRep objects are sorted in descending order by delegated amount.
    """

    def __init__(self, flags: PRepFlag = PRepFlag.NONE):
        self._flags: 'PRepFlag' = flags
        self._active_prep_dict = {}
        self._active_prep_list = SortedList()
        self._inactive_prep_dict = {}

    def is_frozen(self) -> bool:
        return bool(self._flags & PRepFlag.FROZEN)

    def is_flag_on(self, flags: 'PRepFlag') -> bool:
        return (self._flags & flags) == flags

    def load(self, context: 'IconScoreContext'):
        """Load P-Rep list from StateDB on startup

        :param context:
        :return:
        """
        for prep in context.storage.prep.get_prep_iterator():
            self._active_prep_dict[prep.address] = prep
            if prep.status == PRepStatus.ACTIVE:
                self._active_prep_list.add(prep)

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

        self._flags |= PRepFlag.DIRTY

        assert len(self._active_prep_dict) == len(self._active_prep_list)

    def replace(self, prep: 'PRep'):
        assert prep.status == PRepStatus.ACTIVE

        self._check_access_permission()

        old_prep: 'PRep' = self._active_prep_dict.get(prep.address)
        if old_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(prep.address)}")

        if id(old_prep) == id(prep):
            return

        self._active_prep_list.remove(old_prep)

        self._active_prep_dict[prep.address] = prep
        self._active_prep_list.add(prep)

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
        assert prep.status == PRepStatus.ACTIVE

        self._active_prep_list.remove(prep)
        del self._active_prep_dict[address]

        prep.status = status
        self._inactive_prep_dict[address] = prep

        assert len(self._active_prep_dict) == len(self._active_prep_list)
        return prep

    def set_to_prep(self, address: 'Address', **kwargs):
        """Update P-Rep properties from setPRep JSON-RP API

        :param address:
        :param kwargs:
        :return:
        """
        Logger.debug(tag="PREP", msg=f"set_to_prep() start: address({address}) kwargs({kwargs})")

        assert isinstance(address, Address)

        self._check_access_permission()

        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        if prep.is_frozen():
            self._active_prep_list.remove(prep)

            # copy on write
            new_prep: 'PRep' = prep.copy(PRepFlag.NONE)
            new_prep.set(**kwargs)

            self._active_prep_dict[new_prep.address] = new_prep
            self._active_prep_list.add(new_prep)
        else:
            prep.set(**kwargs)

        toggle_flags(self._flags, PRepFlag.DIRTY, True)

        Logger.debug(tag="PREP", msg=f"set_to_prep() end")

    def set_delegated_to_prep(self, address: 'Address', delegated: int):
        """
        :param address:
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

    def get_by_index(self, index: int) -> 'PRep':
        return self._active_prep_list[index]

    def get_by_address(self, address: 'Address') -> Optional['PRep']:
        """Returns an active P-Rep with a given address

        :param address: The address of a P-Rep
        :return: The instance of a PRep which has a given address
        """
        return self._active_prep_dict.get(address)

    def __len__(self) -> int:
        assert len(self._active_prep_list) == len(self._active_prep_dict)
        return len(self._active_prep_list)

    def get_preps(self, start_index: int, size: int) -> List['PRep']:
        """Returns

        :return: P-Rep list
        """
        return self._active_prep_list[start_index:start_index + size]

    def get_snapshot(self) -> 'PRepContainer':
        if not self.is_frozen():
            raise AccessDeniedException("Failed to get PRepContaienr snapshot")

        return self.copy(PRepFlag.FROZEN)

    def index(self, address: 'Address') -> int:
        """Returns the index of a given address in active_prep_list

        :return: zero-based index
        """
        prep: 'PRep' = self._active_prep_dict.get(address)
        if prep is None:
            Logger.info(tag="PREP", msg=f"P-Rep not found on get_ranking: {str(address)}")
            return -1

        index: int = self._active_prep_list.index(prep)
        assert index >= 0

        return index

    def copy(self, flags: 'PRepFlag') -> 'PRepContainer':
        preps = PRepContainer(flags)

        preps._active_prep_dict.update(self._active_prep_dict)
        preps._active_prep_list.extend(self._active_prep_list)
        preps._inactive_prep_dict.update(self._inactive_prep_dict)

        return preps

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("PRepContainer access denied")
