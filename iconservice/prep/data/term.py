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
from typing import TYPE_CHECKING, List, Iterable, Optional, Dict

from iconcommons.logger import Logger
from ... import utils
from ...base.exception import AccessDeniedException
from ...icon_constant import PRepStatus, PenaltyReason, TermFlag
from ...utils import bytes_to_hex
from ...utils.hashing.hash_generator import RootHashGenerator

if TYPE_CHECKING:
    from ...base.address import Address
    from .prep import PRep


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

    def __eq__(self, other: 'PRepSnapshot') -> bool:
        return self.address == other.address \
               and self.delegated == other.delegated


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
        self._sequence = sequence

        self._start_block_height = start_block_height
        self._period = period

        self._irep = irep
        self._total_supply = total_supply
        self._total_delegated = total_delegated
        self._total_elected_prep_delegated = 0
        self._total_elected_prep_delegated_snapshot: int = 0

        self._main_preps: List['PRepSnapshot'] = []
        self._sub_preps: List['PRepSnapshot'] = []
        self._preps_dict: Dict['Address', 'PRepSnapshot'] = {}

        # made from main P-Rep addresses
        self._merkle_root_hash: Optional[bytes] = None
        self._is_frozen: bool = False
        self._flags: 'TermFlag' = TermFlag.NONE

    @property
    def flags(self) -> 'TermFlag':
        return self._flags

    def is_dirty(self):
        return utils.is_any_flag_on(self._flags, TermFlag.ALL)

    def on_main_prep_changed(self, flag: 'TermFlag'):
        self._check_access_permission()
        self._flags |= flag

    def is_frozen(self) -> bool:
        return self._is_frozen

    def freeze(self):
        self._is_frozen = True
        self._flags = TermFlag.NONE

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("Term access denied")

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        return \
            f"Term:" \
            f"seq={self._sequence} " \
            f"start_block_height={self._start_block_height} " \
            f"period={self._period} " \
            f"irep={self._irep}" \
            f"total_supply={self._total_supply} " \
            f"total_delegated={self._total_delegated} " \
            f"total_elected_prep_delegated={self._total_elected_prep_delegated} " \
            f"_total_elected_prep_delegated_snapshot={self._total_elected_prep_delegated_snapshot} " \
            f"root_hash={bytes_to_hex(self._merkle_root_hash)}"

    def __contains__(self, address: 'Address') -> bool:
        """Check whether the given address is an elected P-Rep

        :param address: P-Rep address
        :return: True(elected P-Rep), False(non-elected P-Rep)
        """
        return address in self._preps_dict

    def __len__(self) -> int:
        """Return the number of main P-Reps and sub P-Reps

        :return:
        """
        return len(self._preps_dict)

    def __eq__(self, other: 'Term') -> bool:
        return isinstance(other, Term) \
            and self._sequence == other._sequence \
            and self._start_block_height == other._start_block_height \
            and self._period == other._period \
            and self._irep == other._irep \
            and self._total_supply == other._total_supply \
            and self._total_delegated == other._total_delegated \
            and self._total_elected_prep_delegated == other._total_elected_prep_delegated \
            and self._total_elected_prep_delegated_snapshot == other._total_elected_prep_delegated_snapshot \
            and self._main_preps == other._main_preps \
            and self._sub_preps == other._sub_preps \
            and self._preps_dict == other._preps_dict \
            and self._merkle_root_hash == other._merkle_root_hash

    def is_main_prep(self, address: 'Address') -> bool:
        for prep_snapshot in self._main_preps:
            if address == prep_snapshot.address:
                return True

        return False

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

    # @total_supply.setter
    # def total_supply(self, value: int):
    #     self._total_supply = value

    @property
    def total_delegated(self) -> int:
        """Total amount of delegation which all active P-Reps got when this term is started
        """
        return self._total_delegated

    @property
    def total_elected_prep_delegated(self) -> int:
        """The sum of delegated amount which only main and sub P-Reps got

        :return:
        """
        return self._total_elected_prep_delegated

    @property
    def total_elected_prep_delegated_snapshot(self) -> int:
        """The sum of delegated amount which only main and sub P-Reps got on start Term

        :return:
        """
        return self._total_elected_prep_delegated_snapshot

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

    def is_in_term(self, block_height: int):
        return self.start_block_height <= block_height <= self.end_block_height

    def set_preps(self,
                  it: Iterable['PRep'],
                  main_prep_count: int,
                  elected_prep_count: int):
        """Set elected P-Rep data to term

        This method MUST BE called at the end of the term

        :param it:
        :param main_prep_count:
        :param elected_prep_count:
        :return:
        """

        self._main_preps.clear()
        self._sub_preps.clear()
        self._preps_dict.clear()

        # Main and sub P-Reps
        total_elected_prep_delegated: int = 0

        for i, prep in enumerate(it):
            if i >= elected_prep_count:
                break

            # active and no penalty
            assert prep.is_electable()

            snapshot = PRepSnapshot(prep.address, prep.delegated)
            total_elected_prep_delegated += prep.delegated

            if len(self._main_preps) < main_prep_count:
                self._main_preps.append(snapshot)
            else:
                self._sub_preps.append(snapshot)

            self._preps_dict[snapshot.address] = snapshot

        self._total_elected_prep_delegated_snapshot = total_elected_prep_delegated
        self._total_elected_prep_delegated = total_elected_prep_delegated

        self._generate_root_hash()
        self._flags = TermFlag.NONE

    def update_invalid_elected_preps(self, invalid_elected_preps: Iterable['PRep']):
        """Update main and sub P-Reps with invalid elected P-Reps

        :param invalid_elected_preps:
            elected P-Reps that cannot keep governance during this term as their penalties
        :return:
        """
        self._check_access_permission()
        flags: 'TermFlag' = TermFlag.NONE

        for prep in invalid_elected_preps:
            if self._remove_invalid_main_prep(prep) >= 0:
                flags |= TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS
                continue
            if self._remove_invalid_sub_prep(prep) >= 0:
                flags |= TermFlag.SUB_PREPS
                continue

            raise AssertionError(f"{prep.address} not in elected P-Reps: {self}")

        if utils.is_all_flag_on(flags, TermFlag.MAIN_PREPS):
            self._generate_root_hash()

        self._flags |= flags

    def _remove_invalid_main_prep(self, invalid_prep: 'PRep') -> int:
        """Replace an invalid main P-Rep with the top-ordered sub P-Rep

        :param invalid_prep: an invalid main P-Rep
        :return: the index of an given address in self._main_preps
            if not exists, returns -1
        """

        address = invalid_prep.address
        index: int = self._index_of_prep(self._main_preps, address)
        if index < 0:
            return index

        invalid_prep_snapshot = self._main_preps[index]

        if len(self._sub_preps) == 0:
            self._main_preps.pop(index)
            Logger.warning(tag=self.TAG,
                           msg=f"Not enough sub P-Rep to replace an invalid main P-Rep")
        else:
            self._main_preps[index] = self._sub_preps.pop(0)
            Logger.info(
                tag=self.TAG,
                msg=f"Replace a main P-Rep: "
                    f"index={index} {address} -> {self._main_preps[index].address}")

        self._reduce_total_elected_prep_delegated(invalid_prep, invalid_prep_snapshot.delegated)
        del self._preps_dict[address]

        return index

    def _remove_invalid_sub_prep(self, invalid_prep: 'PRep') -> int:
        """Remove an invalid sub P-Rep from self._sub_preps

        :param invalid_prep: an invalid sub P-Rep
        :return: the index of an given address in self._sub_preps
            if not exists, returns -1
        """
        index: int = self._index_of_prep(self._sub_preps, invalid_prep.address)

        if index >= 0:
            invalid_prep_snapshot = self._sub_preps.pop(index)
            self._reduce_total_elected_prep_delegated(invalid_prep, invalid_prep_snapshot.delegated)
            del self._preps_dict[invalid_prep.address]

        return index

    def _reduce_total_elected_prep_delegated(self, invalid_prep: 'PRep', delegated: int):
        """Reduce total_elected_prep_delegated by the delegated amount of the given invalid P-Rep

        :param invalid_prep:
        :param delegated:
        :return:
        """

        # This code is preserved only for state backward compatibility.
        # After revision 7, B2 reward is not provided to the P-Rep
        # which got penalized for consecutive 660 blocks validation failure
        if invalid_prep.status != PRepStatus.ACTIVE \
                or invalid_prep.penalty != PenaltyReason.BLOCK_VALIDATION:
            self._total_elected_prep_delegated_snapshot -= delegated
            Logger.info(tag=self.TAG,
                        msg="total_elected_prep_delegated_snapshot is changed: "
                            f"delta={-delegated} "
                            f"total_elected_prep_delegated_snapshot={self._total_elected_prep_delegated_snapshot}")

        self._total_elected_prep_delegated -= delegated
        Logger.info(tag=self.TAG,
                    msg="total_elected_prep_delegated is changed: "
                        f"delta={-delegated} "
                        f"total_elected_prep_delegated={self._total_elected_prep_delegated}")

    @classmethod
    def _index_of_prep(cls, preps: List['PRepSnapshot'], address: 'Address') -> int:
        for i, snapshot in enumerate(preps):
            if address == snapshot.address:
                return i

        return -1

    def _generate_root_hash(self):
        def _gen(snapshots: Iterable['PRepSnapshot']) -> bytes:
            for snapshot in snapshots:
                yield snapshot.address.to_bytes_including_prefix()

        self._merkle_root_hash: bytes = \
            RootHashGenerator.generate_root_hash(values=_gen(self._main_preps), do_hash=True)

    @classmethod
    def from_list(cls, data: List,
                  block_height: int,
                  total_elected_prep_delegated_from_rc: int) -> 'Term':
        assert data[0] == cls._VERSION
        sequence: int = data[1]
        start_block_height: int = data[2]
        period: int = data[3]
        irep: int = data[4]
        total_supply: int = data[5]
        total_delegated: int = data[6]
        main_preps = data[7]
        sub_preps = data[8]
        total_elected_prep_delegated = 0

        term = Term(sequence, start_block_height, period, irep, total_supply, total_delegated)

        for address, delegated in main_preps:
            snapshot = PRepSnapshot(address, delegated)
            term._main_preps.append(snapshot)
            term._preps_dict[address] = snapshot
            total_elected_prep_delegated += delegated

        for address, delegated in sub_preps:
            snapshot = PRepSnapshot(address, delegated)
            term._sub_preps.append(snapshot)
            term._preps_dict[address] = snapshot
            total_elected_prep_delegated += delegated

        term._total_elected_prep_delegated = total_elected_prep_delegated

        if block_height == start_block_height - 1 or total_elected_prep_delegated_from_rc <= 0:
            # In the case of the first term (prevote -> decentralization),
            # total_elected_prep_delegated_from_rc can be 0.
            # and
            # fix IS-965 Sync fails on block height 10491442 when sync by using a master branch
            total_elected_prep_delegated_from_rc = total_elected_prep_delegated
        term._total_elected_prep_delegated_snapshot = total_elected_prep_delegated_from_rc

        term._generate_root_hash()

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
            [[snapshot.address, snapshot.delegated] for snapshot in self._main_preps],
            [[snapshot.address, snapshot.delegated] for snapshot in self._sub_preps],
        ]

    def copy(self) -> 'Term':
        term = copy.copy(self)
        term._is_frozen = False
        term._flags = TermFlag.NONE

        term._main_preps = list(self._main_preps)
        term._sub_preps = list(self._sub_preps)
        term._preps_dict = dict(self._preps_dict)

        return term
