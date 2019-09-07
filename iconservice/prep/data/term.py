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

__all__ = ("Term", "PRepSnapshot")

import copy
import enum
from typing import TYPE_CHECKING, List, Iterable, Union, Optional

from iconcommons.logger import Logger
from ...base.exception import AccessDeniedException
from ...utils.hashing.hash_generator import RootHashGenerator

if TYPE_CHECKING:
    from ...base.address import Address
    from .prep import PRep


class _Flag(enum.Flag):
    NONE = 0
    DIRTY = enum.auto()
    FROZEN = enum.auto()


class PRepSnapshot(object):
    """Contains P-Rep address and the delegated amount when this term started
    """

    def __init__(self, address: 'Address', delegated: int):
        self._address = address
        self._delegated = delegated

    @property
    def address(self) -> 'Address':
        return self._address
    
    @property
    def delegated(self) -> int:
        return self._delegated


class Term(object):
    """Manages P-Rep Term information
    """

    TAG = "TERM"
    _VERSION = 0

    def __init__(self,
                 sequence: int,
                 start_block_height: int,
                 period: int,
                 irep: int,
                 total_supply: int,
                 total_delegated: int):
        self._flag: _Flag = _Flag.NONE
        self._sequence = sequence

        self._start_block_height = start_block_height
        self._period = period

        self._irep = irep
        self._total_supply = total_supply
        self._total_delegated = total_delegated
        self._total_elected_prep_delegated = 0

        self._main_preps: List['PRepSnapshot'] = []
        self._sub_preps: List['PRepSnapshot'] = []

        # made from main P-Rep addresses
        self._merkle_root_hash: Optional[bytes] = None

    def is_frozen(self) -> bool:
        return bool(self._flag & _Flag.FROZEN)

    def is_dirty(self) -> bool:
        return bool(self._flag & _Flag.DIRTY)

    def freeze(self):
        self._flag = _Flag.FROZEN

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("Term access denied")

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        return f"Term(seq={self._sequence} totalSupply=f{self._total_supply})"

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def start_block_height(self) -> int:
        return self._start_block_height

    @property
    def end_block_height(self) -> int:
        return self._start_block_height + self._period - 1

    @property
    def period(self) -> int:
        return self._period

    @property
    def irep(self) -> int:
        """Returns weighted average irep used during a term

        :return: weighted average irep that is calculated with ireps submitted by 22 Main P-Reps
        """
        return self._irep

    @property
    def total_supply(self) -> int:
        return self._total_supply

    @property
    def total_delegated(self) -> int:
        """Total amount of delegation which all active P-Reps got when this term started
        """
        return self._total_delegated

    @property
    def total_elected_prep_delegated(self) -> int:
        """The sum of delegated amount which only main and sub P-Reps got

        :return:
        """
        return self._total_elected_prep_delegated

    @property
    def main_preps(self) -> List['PRepSnapshot']:
        return self._main_preps

    @property
    def sub_preps(self) -> List['PRepSnapshot']:
        return self._sub_preps

    @property
    def preps(self) -> Iterable['PRepSnapshot']:
        for snapshot in self._main_preps:
            yield snapshot
        for snapshot in self._sub_preps:
            yield snapshot

    @property
    def root_hash(self) -> bytes:
        assert isinstance(self._merkle_root_hash, bytes)
        return self._merkle_root_hash

    def set_preps(self,
                  it: Union[Iterable['PRep'], Iterable['PRepSnapshot']],
                  main_prep_count: int,
                  elected_prep_count: int):
        """Set elected P-Rep data to term

        :param it:
        :param main_prep_count:
        :param elected_prep_count:
        :return:
        """

        self._main_preps.clear()
        self._sub_preps.clear()

        # Main and sub P-Reps
        total_elected_prep_delegated: int = 0

        for i, prep in enumerate(it):
            if i >= elected_prep_count:
                break

            snapshot = PRepSnapshot(prep.address, prep.delegated)
            total_elected_prep_delegated += prep.delegated

            if len(self._main_preps) < main_prep_count:
                self._main_preps.append(snapshot)
            else:
                self._sub_preps.append(snapshot)

        self._total_elected_prep_delegated = total_elected_prep_delegated
        self._merkle_root_hash: bytes = self._generate_root_hash(self._main_preps)

    def set_main_preps(self,
                       it: Union[Iterable['PRep'], Iterable['PRepSnapshot']],
                       size: int):
        self._set_preps(it, size, self._main_preps)

    def set_sub_preps(self,
                      it: Union[Iterable['PRep'], Iterable['PRepSnapshot']],
                      size: int):
        self._set_preps(it, size, self._sub_preps)

    @classmethod
    def _set_preps(cls,
                   it: Union[Iterable['PRep'], Iterable['PRepSnapshot']],
                   size: int,
                   preps: List['PRepSnapshot']):
        preps.clear()

        for item in it:
            if len(preps) >= size:
                break

            snapshot = PRepSnapshot(item.address, item.delegated)
            preps.append(snapshot)

    def update(self, invalid_elected_preps: Iterable['Address']):
        self._check_access_permission()

        for address in invalid_elected_preps:
            if self._replace_invalid_main_prep(address) >= 0:
                continue
            if self._remove_invalid_sub_prep(address) >= 0:
                continue

            raise AssertionError(f"{address} not in term: {self}")

        if self.is_dirty():
            self._merkle_root_hash: bytes = self._generate_root_hash(self._main_preps)

    def _replace_invalid_main_prep(self, address: 'Address') -> int:
        """Replace an invalid main P-Rep with the top-ordered sub P-Rep

        :param address: The address of an invalid main P-Rep
        :return: the index of an given address in self._main_preps
            if not exists, returns -1
        """

        index: int = self._index_of_prep(self._main_preps, address)
        if index < 0:
            return index

        if len(self._sub_preps) == 0:
            self._main_preps.pop(index)
            Logger.warning(tag=self.TAG,
                           msg=f"Not enough sub P-Rep to replace an invalid main P-Rep")

        self._main_preps[index] = self._sub_preps.pop(0)
        Logger.info(
            tag=self.TAG,
            msg=f"Replace a main P-Rep: "
                f"index={index} {address} -> {self._main_preps[index].address}")

        self._flag |= _Flag.DIRTY
        return index

    def _remove_invalid_sub_prep(self, address: 'Address') -> int:
        """Remove an invalid sub P-Rep from self._sub_preps

        :param address: The address of an invalid sub P-Rep
        :return: the index of an given address in self._sub_preps
            if not exists, returns -1
        """
        index: int = self._index_of_prep(self._sub_preps, address)
        if index < 0:
            return index

        self._sub_preps.pop(index)
        self._flag |= _Flag.DIRTY

    @classmethod
    def _index_of_prep(cls, preps: List['PRepSnapshot'], address: 'Address') -> int:
        for i, snapshot in enumerate(preps):
            if address == snapshot.address:
                return i

        return -1

    @classmethod
    def _generate_root_hash(cls, preps: Iterable['PRepSnapshot']) -> bytes:

        def _gen(snapshots: Iterable['PRepSnapshot']) -> bytes:
            for snapshot in snapshots:
                yield snapshot.address.to_bytes_including_prefix()

        return RootHashGenerator.generate_root_hash(values=_gen(preps), do_hash=True)

    @classmethod
    def from_list(cls, data: List) -> 'Term':
        assert data[0] == cls._VERSION
        sequence: int = data[1]
        start_block_height: int = data[2]
        period: int = data[3]
        irep: int = data[4]
        total_supply: int = data[5]
        total_delegated: int = data[6]
        main_preps = data[7]
        sub_preps = data[8]

        term = Term(sequence, start_block_height, period, irep, total_supply, total_delegated)

        for address, delegated in main_preps:
            term._main_preps.append(PRepSnapshot(address, delegated))

        for address, delegated in sub_preps:
            term._sub_preps.append(PRepSnapshot(address, delegated))

        return term

    def to_list(self) -> List:
        return [
            self._VERSION,
            self._sequence,
            self._start_block_height,
            self._period,
            self._irep,
            self._total_supply,
            self._total_delegated,
            [(snapshot.address, snapshot.delegated) for snapshot in self._main_preps],
            [(snapshot.address, snapshot.delegated) for snapshot in self._sub_preps],
        ]

    def copy(self) -> 'Term':
        term = copy.copy(self)
        term._flag = _Flag.NONE

        return term
