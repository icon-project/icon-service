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
from .prep import PRep, PRepStatus
from .sorted_list import SortedList
from ... import utils
from ...base.address import Address
from ...base.exception import InvalidParamsException, AccessDeniedException
from ...icon_constant import PRepContainerFlag


class PRepContainer(object):
    """Contains PRep objects

    P-Rep PRep object contains information on registration and delegation.
    PRep objects are sorted in descending order by delegated amount.
    """
    _TAG = "PREP"

    def __init__(self, is_frozen: bool = False, total_prep_delegated: int = 0):
        self._is_frozen: bool = is_frozen
        # Total amount of delegated which all active P-Reps have
        self._total_prep_delegated: int = total_prep_delegated
        # Active P-Rep list ordered by delegated amount
        self._active_prep_list = SortedList()
        self._prep_dict = {}
        self._flags: 'PRepContainerFlag' = PRepContainerFlag.NONE

    def is_frozen(self) -> bool:
        return self._is_frozen

    def is_dirty(self) -> bool:
        return utils.is_all_flag_on(self._flags, PRepContainerFlag.DIRTY)

    def size(self, active_prep_only: bool = False) -> int:
        """Returns the number of active P-Reps

        :return: The number of active P-Reps
        """
        if active_prep_only:
            return len(self._active_prep_list)
        else:
            return len(self._prep_dict)

    @property
    def total_delegated(self) -> int:
        """Returns total amount of delegated which all active P-Reps have

        :return:
        """
        assert self._total_prep_delegated >= 0
        return self._total_prep_delegated

    def freeze(self):
        """Freeze data in PRepContainer
        Freezing makes all data in PRepContainer immutable

        :return:
        """
        if self.is_frozen():
            return

        for prep in self._prep_dict.values():
            if not prep.is_frozen():
                prep.freeze()

        self._flags = PRepContainerFlag.NONE
        self._is_frozen: bool = True

    def add(self, prep: 'PRep'):
        self._check_access_permission()

        if prep.address in self._prep_dict:
            raise InvalidParamsException("P-Rep already exists")

        self._add(prep)
        self._flags |= PRepContainerFlag.DIRTY

    def _add(self, prep: 'PRep'):

        self._prep_dict[prep.address] = prep

        if prep.status == PRepStatus.ACTIVE:
            self._active_prep_list.add(prep)

            # Update self._total_prep_delegated
            self._total_prep_delegated += prep.delegated
            assert self._total_prep_delegated >= 0

    def remove(self, address: 'Address') -> Optional['PRep']:
        """Remove a prep indicated by address from self._active_prep_list and self._prep_dict

        :param address:
        :return:
        """
        self._check_access_permission()

        prep: Optional['PRep'] = self._remove(address)
        if prep is not None:
            self._flags |= PRepContainerFlag.DIRTY

        return prep

    def _remove(self, address: 'Address') -> Optional['PRep']:
        prep: Optional['PRep'] = self._prep_dict.get(address)
        if prep is not None:
            if prep.status == PRepStatus.ACTIVE:
                self._active_prep_list.remove(prep)
                self._total_prep_delegated -= prep.delegated

            del self._prep_dict[address]

        return prep

    def replace(self, new_prep: 'PRep') -> Optional['PRep']:
        """Replace old_prep with new_prep

        :param new_prep:
        :return:
        """
        self._check_access_permission()

        old_prep: Optional['PRep'] = self._prep_dict.get(new_prep.address)
        if id(old_prep) == id(new_prep):
            Logger.debug(tag=self._TAG, msg="No need to replace the same P-Rep")
            return None

        self._remove(new_prep.address)
        self._add(new_prep)
        self._flags |= PRepContainerFlag.DIRTY

        return old_prep

    def contains(self, address: 'Address', active_prep_only: bool = True) -> bool:
        """Check whether the P-Rep is contained regardless of its PRepStatus

        :param address: Address
        :param active_prep_only: bool
        :return: True(contained) False(not contained)
        """
        prep: 'PRep' = self._prep_dict.get(address)
        if prep is None:
            return False

        return prep.status == PRepStatus.ACTIVE if active_prep_only else True

    def __iter__(self):
        """Active P-Rep iterator

        :return:
        """
        for prep in self._active_prep_list:
            yield prep

    def get_by_index(self, index: int) -> Optional['PRep']:
        """Returns an active P-Rep with a given index

        :param index:
        :return:
        """
        return self._active_prep_list.get(index)

    def get_by_address(self, address: 'Address') -> Optional['PRep']:
        """Returns an P-Rep with a given address regardless of its status

        :param address: The address of a P-Rep
        :return: The instance of a PRep which has a given address
        """
        return self._prep_dict.get(address)

    def get_preps(self, start_index: int, size: int) -> List['PRep']:
        """Returns active P-Reps ranging from start_index to start_index + size - 1

        :return: P-Rep list
        """
        return self._active_prep_list[start_index:start_index + size]

    def get_inactive_preps(self) -> List['PRep']:
        """Returns inactive P-Reps which is unregistered or receiving prep disqualification or low productivity penalty.
        This method does not care about the order of P-Rep list

        :return: Inactive Prep list
        """

        # Collect P-Reps which is unregistered or receiving prep disqualification or low productivity penalty.
        def _func(node: 'PRep') -> bool:
            return node.status != PRepStatus.ACTIVE

        inactive_preps = list(filter(_func, self._prep_dict.values()))
        return inactive_preps

    def index(self, address: 'Address') -> int:
        """Returns the index of a given address in active_prep_list

        :return: zero-based index
        """
        prep: 'PRep' = self._prep_dict.get(address)
        if prep is None:
            Logger.info(tag="PREP", msg=f"P-Rep not found: {address}")
            return -1

        if prep.status == PRepStatus.ACTIVE:
            return self._active_prep_list.index(prep)

        return -1

    def copy(self, mutable: bool) -> 'PRepContainer':
        """Copy PRepContainer without changing PRep objects

        :param mutable:
        :return:
        """
        preps = PRepContainer(is_frozen=not mutable, total_prep_delegated=self._total_prep_delegated)

        preps._prep_dict.update(self._prep_dict)
        preps._active_prep_list.extend(self._active_prep_list)

        return preps

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("PRepContainer access denied")
