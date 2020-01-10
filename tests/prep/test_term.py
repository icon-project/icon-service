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

import copy
import random
import unittest
from typing import List
from unittest.mock import Mock

from iconservice import utils
from iconservice.base.address import Address, AddressPrefix
from iconservice.icon_constant import (
    PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, TERM_PERIOD,
    IconScoreContextType, PenaltyReason, PRepStatus, TermFlag
)
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx import IcxStorage
from iconservice.prep import PRepStorage
from iconservice.prep.data import PRep, Term
from iconservice.utils import ContextStorage

context = IconScoreContext(IconScoreContextType.DIRECT)
context.storage = ContextStorage(deploy=None, fee=None, icx=Mock(spec=IcxStorage), iiss=None,
                                 issue=None, rc=None, prep=Mock(spec=PRepStorage), meta=None)
context.storage.prep.put_term = Mock()


def _check_prep_snapshots_in_term(term: 'Term'):
    assert len(term) == len(term.main_preps) + len(term.sub_preps)

    for snapshot in term.preps:
        assert snapshot.address in term


class TestTerm(unittest.TestCase):
    def setUp(self) -> None:
        self.sequence = random.randint(0, 1000)
        self.start_block_height = random.randint(0, 1000)
        self.period = TERM_PERIOD
        self.irep = random.randint(10000, 50000)
        self.total_supply = 800_600_000
        self.total_delegated = 2000 * 10 ** 18

        self.term = Term(
            sequence=self.sequence,
            start_block_height=self.start_block_height,
            period=self.period,
            irep=self.irep,
            total_supply=self.total_supply,
            total_delegated=self.total_delegated
        )
        assert not self.term.is_frozen()
        assert not self.term.is_dirty()
        _check_prep_snapshots_in_term(self.term)

        keys = "sequence", "start_block_height", "period", "irep", "total_supply", "total_delegated"

        for key in keys:
            assert getattr(self.term, key) == getattr(self, key)

        self.preps = []
        self.total_elected_prep_delegated = 0
        for i in range(PREP_MAIN_AND_SUB_PREPS + 10):
            delegated = 100 * 10 ** 18 - i

            self.preps.append(PRep(
                Address.from_prefix_and_int(AddressPrefix.EOA, i),
                delegated=delegated
            ))

            if i < PREP_MAIN_AND_SUB_PREPS:
                self.total_elected_prep_delegated += delegated

        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        assert not self.term.is_dirty()

    def test_set_preps(self):
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        _check_prep_snapshots_in_term(self.term)

        assert not self.term.is_frozen()
        assert self.term.total_elected_prep_delegated == self.total_elected_prep_delegated
        assert len(self.term.main_preps) == PREP_MAIN_PREPS
        assert len(self.term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS

        for prep, prep_snapshot in zip(self.preps, self.term.main_preps):
            assert prep.address == prep_snapshot.address
            assert prep.delegated == prep_snapshot.delegated

        for prep, prep_snapshot in zip(self.preps[PREP_MAIN_PREPS:], self.term.sub_preps):
            assert prep.address == prep_snapshot.address
            assert prep.delegated == prep_snapshot.delegated

        for prep, prep_snapshot in zip(self.preps, self.term.preps):
            assert prep.address == prep_snapshot.address
            assert prep.delegated == prep_snapshot.delegated

    def test_update_preps_with_critical_penalty(self):
        revision: int = 0
        # Remove an invalid Main P-Rep which gets a penalty
        penalties = [
            PenaltyReason.LOW_PRODUCTIVITY,
            PenaltyReason.PREP_DISQUALIFICATION
        ]

        for penalty in penalties:
            self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
            _check_prep_snapshots_in_term(self.term)
            assert isinstance(self.term.root_hash, bytes)
            assert len(self.term.root_hash) == 32

            term = self.term.copy()
            _check_prep_snapshots_in_term(term)
            invalid_main_prep = copy.deepcopy(self.preps[0])
            invalid_main_prep.penalty = penalty
            invalid_elected_preps: List['PRep'] = [invalid_main_prep]

            term.update_invalid_elected_preps(invalid_elected_preps)

            _check_prep_snapshots_in_term(term)
            assert len(term.main_preps) == PREP_MAIN_PREPS
            assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS - len(invalid_elected_preps)
            assert isinstance(term.root_hash, bytes)
            assert term.root_hash != self.term.root_hash
            assert term.total_elected_prep_delegated == self.total_elected_prep_delegated - invalid_main_prep.delegated
            assert not term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
            assert utils.is_all_flag_on(term.flags, TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS)
            assert term.is_dirty()

    def test_update_preps_with_block_validation_penalty(self):
        revision: int = 0
        # Remove an invalid Main P-Rep which gets a block validation penalty
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        _check_prep_snapshots_in_term(self.term)
        assert isinstance(self.term.root_hash, bytes)
        assert len(self.term.root_hash) == 32

        term = self.term.copy()
        _check_prep_snapshots_in_term(term)
        invalid_main_prep = copy.deepcopy(self.preps[0])
        invalid_main_prep.penalty = PenaltyReason.BLOCK_VALIDATION
        invalid_elected_preps: List['PRep'] = [invalid_main_prep]

        term.update_invalid_elected_preps(invalid_elected_preps)
        _check_prep_snapshots_in_term(term)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS - len(invalid_elected_preps)
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash
        assert term.total_elected_prep_delegated == self.total_elected_prep_delegated - invalid_main_prep.delegated
        assert not term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert utils.is_all_flag_on(term.flags, TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS)
        assert term.is_dirty()

    def test_update_preps_with_unregistered_prep(self):
        revision: int = 0
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        _check_prep_snapshots_in_term(self.term)

        assert isinstance(self.term.root_hash, bytes)
        assert len(self.term.root_hash) == 32

        term = self.term.copy()
        _check_prep_snapshots_in_term(term)
        invalid_main_prep = copy.deepcopy(self.preps[0])
        invalid_main_prep.status = PRepStatus.UNREGISTERED
        invalid_elected_preps: List['PRep'] = [invalid_main_prep]

        term.update_invalid_elected_preps(invalid_elected_preps)
        _check_prep_snapshots_in_term(term)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS - len(invalid_elected_preps)
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash
        assert term.total_elected_prep_delegated == self.total_elected_prep_delegated - invalid_main_prep.delegated
        assert not term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert utils.is_all_flag_on(term.flags, TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS)
        assert term.is_dirty()

    def test_update_preps_with_sub_preps_only(self):
        revision: int = 0
        # Remove all sub P-Reps
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        _check_prep_snapshots_in_term(self.term)

        term = self.term.copy()
        invalid_elected_preps: List['PRep'] = []
        for i in range(PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS):
            prep = self.preps[i]
            prep.penalty = PenaltyReason.LOW_PRODUCTIVITY
            invalid_elected_preps.append(prep)
        assert len(invalid_elected_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS

        term.update_invalid_elected_preps(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == 0
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash == self.term.root_hash
        assert not term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert not term.flags & TermFlag.MAIN_PREPS
        assert utils.is_all_flag_on(term.flags, TermFlag.SUB_PREPS)
        assert term.is_dirty()

    def test_update_preps_2(self):
        # Remove all main P-Reps
        term = self.term.copy()
        revision: int = 0
        _check_prep_snapshots_in_term(term)

        invalid_elected_preps: List['PRep'] = [prep for prep in self.preps[:PREP_MAIN_PREPS]]
        term.update_invalid_elected_preps(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS * 2
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash

        # Remove all P-Reps except for a P-Rep
        term = self.term.copy()
        _check_prep_snapshots_in_term(term)

        invalid_elected_preps: List['PRep'] = [prep for prep in self.preps[1:PREP_MAIN_AND_SUB_PREPS]]
        term.update_invalid_elected_preps(invalid_elected_preps)
        assert len(term.main_preps) == 1
        assert len(term.sub_preps) == 0
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash
        assert term.flags == term.flags, TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS
        assert not term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert utils.is_all_flag_on(term.flags, TermFlag.MAIN_PREPS | TermFlag.SUB_PREPS)
        assert term.is_dirty()

    def test_to_list_and_from_list(self):
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        assert not self.term.is_dirty()
        assert self.term.flags == TermFlag.NONE
        _check_prep_snapshots_in_term(self.term)

        new_term = Term.from_list(self.term.to_list(), 0, self.term.total_elected_prep_delegated_snapshot)
        _check_prep_snapshots_in_term(new_term)

        assert self.term == new_term

    def test__contain__(self):
        term = self.term
        term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        assert not term.is_dirty()
        assert term.flags == TermFlag.NONE

        _check_prep_snapshots_in_term(term)

        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS
        assert len(term) == PREP_MAIN_AND_SUB_PREPS

    def test_on_main_prep_p2p_endpoint_updated(self):
        term = self.term
        term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        assert not term.is_dirty()
        assert term.flags == TermFlag.NONE

        term.on_main_prep_p2p_endpoint_updated()
        assert term.is_dirty()
        assert term.flags == TermFlag.MAIN_PREP_P2P_ENDPOINT
