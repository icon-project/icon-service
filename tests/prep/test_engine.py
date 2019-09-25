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

import os
import random
import unittest
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.block import Block
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.icon_constant import PRepGrade, IconScoreContextType, PRepStatus, PenaltyReason
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextFactory
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.prep import PRepEngine
from iconservice.prep.data import PRep, PRepContainer, Term
from iconservice.utils import icx_to_loop


def _create_context() -> 'IconScoreContext':
    step_counter = Mock(spec=IconScoreStepCounterFactory)
    context_factory = IconScoreContextFactory(step_counter)
    block = Block(block_height=100,
                  block_hash=os.urandom(32),
                  timestamp=0,
                  prev_hash=os.urandom(32),
                  cumulative_fee=0)

    return context_factory.create(IconScoreContextType.INVOKE, block)


def _create_term(total_supply: int, total_delegated: int):
    return Term(sequence=0,
                start_block_height=100,
                period=43120,
                irep=icx_to_loop(50000),
                total_supply=total_supply,
                total_delegated=total_delegated)


def _create_preps(size: int):
    preps = PRepContainer()

    # Create dummy preps
    for i in range(size):
        address = Address.from_prefix_and_int(AddressPrefix.EOA, i)
        delegated = icx_to_loop(1000 - i)

        prep = PRep(address, block_height=i, delegated=delegated)
        prep.freeze()

        assert prep.grade == PRepGrade.CANDIDATE
        assert prep.delegated == delegated
        assert prep.block_height == i
        preps.add(prep)

    return preps


def _check_prep_grades(new_preps: 'PRepContainer', main_prep_count: int, elected_prep_count: int):
    for i, prep in enumerate(new_preps):
        if i < main_prep_count:
            assert prep.grade == PRepGrade.MAIN
        elif i < elected_prep_count:
            assert prep.grade == PRepGrade.SUB
        else:
            assert prep.grade == PRepGrade.CANDIDATE


def _check_prep_grades2(new_preps: 'PRepContainer', new_term: 'Term'):
    main_prep_count = len(new_term.main_preps)
    elected_prep_count = len(new_term)

    for i, snapshot in enumerate(new_term.preps):
        prep = new_preps.get_by_address(snapshot.address)

        if i < main_prep_count:
            assert prep.grade == PRepGrade.MAIN
        elif i < elected_prep_count:
            assert prep.grade == PRepGrade.SUB

    for prep in new_preps:
        if prep.address in new_term:
            assert prep.grade in (PRepGrade.MAIN, PRepGrade.SUB)
        else:
            assert prep.grade == PRepGrade.CANDIDATE


class TestEngine(unittest.TestCase):
    def setUp(self) -> None:
        context = Mock()

        self.total_supply = icx_to_loop(800_460_000)
        self.total_delegated = 0

        main_prep_count = PREP_MAIN_PREPS
        elected_prep_count = PREP_MAIN_AND_SUB_PREPS
        sub_prep_count = elected_prep_count - main_prep_count

        new_preps: 'PRepContainer' = _create_preps(size=elected_prep_count * 2)
        term = Term(sequence=0,
                    start_block_height=100,
                    period=43120,
                    irep=icx_to_loop(50000),
                    total_supply=self.total_supply,
                    total_delegated=self.total_delegated)
        term.set_preps(new_preps, main_prep_count, elected_prep_count)
        assert len(term.main_preps) == main_prep_count
        assert len(term.sub_preps) == elected_prep_count - main_prep_count
        assert len(term) == elected_prep_count

        # Case 0: Network has just decentralized without any delegation
        PRepEngine._update_prep_grades(
            context, new_preps=new_preps, old_term=None, new_term=term)
        assert len(term.main_preps) == main_prep_count
        assert len(term.sub_preps) == sub_prep_count
        assert len(term) == elected_prep_count
        assert len(term) == len(context.storage.prep.put_prep.mock_calls)

        _check_prep_grades(new_preps, main_prep_count, len(term))

        self.term = term
        self.preps = new_preps
        self.main_prep_count = PREP_MAIN_PREPS
        self.elected_prep_count = PREP_MAIN_AND_SUB_PREPS
        self.sub_prep_count = PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS

    def tearDown(self) -> None:
        self.new_preps = None

    def test_update_prep_grades_on_main_prep_unregistration(self):
        context = Mock()

        old_term = self.term
        old_preps = self.preps
        new_term = old_term.copy()
        new_preps = old_preps.copy(mutable=True)

        # Unregister 0-index main P-Rep
        prep = new_preps.get_by_index(0)
        assert prep.grade == PRepGrade.MAIN
        assert prep.address in old_term

        dirty_prep = prep.copy()
        dirty_prep.status = PRepStatus.UNREGISTERED
        new_preps.replace(dirty_prep)
        assert new_preps.is_dirty()

        assert old_preps.get_by_index(0) == prep
        assert new_preps.get_by_index(0) != prep

        # Replace main P-Rep0 with sub P-Rep0
        new_term.update_preps([dirty_prep])
        PRepEngine._update_prep_grades(context, new_preps, old_term, new_term)
        assert len(new_term.main_preps) == self.main_prep_count
        assert len(new_term.sub_preps) == self.sub_prep_count - 1
        assert len(context.storage.prep.put_prep.mock_calls) == 2

        _check_prep_grades(new_preps, self.main_prep_count, len(new_term))
        _check_prep_grades2(new_preps, new_term)
        assert old_term.sub_preps[0] == new_term.main_preps[0]

    def test_update_prep_grades_on_sub_prep_unregistration(self):
        context = Mock()

        old_term = self.term
        old_preps = self.preps
        new_term = old_term.copy()
        new_preps = old_preps.copy(mutable=True)

        # Unregister a sub P-Rep
        index = len(old_term.main_preps)
        prep = new_preps.get_by_index(index)
        assert prep.grade == PRepGrade.SUB
        assert prep.address in old_term

        dirty_prep = prep.copy()
        dirty_prep.status = PRepStatus.UNREGISTERED
        new_preps.replace(dirty_prep)
        assert new_preps.is_dirty()

        assert old_preps.get_by_index(index) == prep
        assert new_preps.get_by_index(index) != prep

        new_term.update_preps([dirty_prep])
        PRepEngine._update_prep_grades(context, new_preps, old_term, new_term)
        _check_prep_grades(new_preps, len(new_term.main_preps), len(new_term))
        assert len(new_term.main_preps) == self.main_prep_count
        assert len(new_term.sub_preps) == self.sub_prep_count - 1
        assert len(context.storage.prep.put_prep.mock_calls) == 1

        for old_snapshot, new_snapshot in zip(old_term.main_preps, new_term.main_preps):
            assert old_snapshot == new_snapshot
        for i, new_snapshot in enumerate(new_term.sub_preps):
            assert new_snapshot == old_term.sub_preps[i + 1]

    def test_update_prep_grades_on_disqualification(self):
        context = Mock()

        states = [PRepStatus.DISQUALIFIED, PRepStatus.DISQUALIFIED, PRepStatus.ACTIVE]
        penalties = [
            PenaltyReason.PREP_DISQUALIFICATION,
            PenaltyReason.LOW_PRODUCTIVITY,
            PenaltyReason.BLOCK_VALIDATION
        ]

        for i in range(len(states)):
            old_term = self.term
            old_preps = self.preps
            new_term = old_term.copy()
            new_preps = old_preps.copy(mutable=True)

            # Disqualify a main P-PRep
            index = random.randint(0, len(old_term.main_preps) - 1)
            prep = new_preps.get_by_index(index)
            assert prep.grade == PRepGrade.MAIN
            assert prep.address in old_term

            dirty_prep = prep.copy()
            dirty_prep.status = states[i]
            dirty_prep.penalty = penalties[i]
            new_preps.replace(dirty_prep)
            assert new_preps.is_dirty()

            assert old_preps.get_by_index(index) == prep
            assert new_preps.get_by_index(index) != prep

            new_term.update_preps([dirty_prep])
            PRepEngine._update_prep_grades(context, new_preps, old_term, new_term)
            if penalties[i] != PenaltyReason.BLOCK_VALIDATION:
                _check_prep_grades(new_preps, len(new_term.main_preps), len(new_term))
            _check_prep_grades2(new_preps, new_term)
            assert len(new_term.main_preps) == self.main_prep_count
            assert len(new_term.sub_preps) == self.sub_prep_count - 1

            j = 0
            for old_snapshot, new_snapshot in zip(old_term.main_preps, new_term.main_preps):
                if j == index:
                    old_snapshot = old_term.sub_preps[0]

                assert old_snapshot == new_snapshot
                j += 1

            for j, new_snapshot in enumerate(new_term.sub_preps):
                assert new_snapshot == old_term.sub_preps[j + 1]

        assert len(context.storage.prep.put_prep.mock_calls) == len(states) * 2

    def test_update_prep_grades_on_multiple_cases(self):
        context = Mock()

        old_term = self.term
        old_preps = self.preps
        new_term = old_term.copy()
        new_preps = old_preps.copy(mutable=True)

        # Main P-Reps
        cases = [
            (PRepStatus.UNREGISTERED, PenaltyReason.NONE),
            (PRepStatus.DISQUALIFIED, PenaltyReason.PREP_DISQUALIFICATION),
            (PRepStatus.DISQUALIFIED, PenaltyReason.LOW_PRODUCTIVITY),
            (PRepStatus.ACTIVE, PenaltyReason.BLOCK_VALIDATION)
        ]
        for case in cases:
            index = random.randint(0, len(new_term.main_preps) - 1)
            prep = new_preps.get_by_index(index)

            dirty_prep = prep.copy()
            dirty_prep.status = case[0]
            dirty_prep.penalty = case[1]
            new_preps.replace(dirty_prep)

            assert new_preps.is_dirty()
            assert old_preps.get_by_address(prep.address) == prep
            assert new_preps.get_by_address(prep.address) != prep
            assert new_preps.get_by_address(prep.address) == dirty_prep

            new_term.update_preps([dirty_prep])

        # Sub P-Rep
        main_prep_count = len(new_term.main_preps)
        assert main_prep_count == len(old_term.main_preps)
        assert len(new_term) == len(old_term) - len(cases)

        for _ in range(3):
            index = random.randint(0, len(new_term.sub_preps) - 1)
            sub_snapshot = new_term.sub_preps[index]
            address = sub_snapshot.address

            prep = new_preps.get_by_address(address)
            assert prep.grade == PRepGrade.SUB

            dirty_prep = prep.copy()
            dirty_prep.status = PRepStatus.UNREGISTERED
            new_preps.replace(dirty_prep)
            assert new_preps.is_dirty()
            assert old_preps.get_by_address(address) == prep
            assert new_preps.get_by_address(address) != prep
            assert new_preps.get_by_address(address) == dirty_prep

            new_term.update_preps([dirty_prep])

        # Candidate P-Rep
        for _ in range(3):
            index = random.randint(1, new_preps.size(active_prep_only=True) - len(new_term) - 1)

            prep = new_preps.get_by_index(len(new_term) + index)
            address = prep.address
            assert prep.grade == PRepGrade.CANDIDATE

            dirty_prep = prep.copy()
            dirty_prep.status = PRepStatus.UNREGISTERED
            new_preps.replace(dirty_prep)
            assert new_preps.is_dirty()
            assert old_preps.get_by_address(address) == prep
            assert new_preps.get_by_address(address) != prep
            assert new_preps.get_by_address(address) == dirty_prep

        PRepEngine._update_prep_grades(context, new_preps, old_term, new_term)
        _check_prep_grades2(new_preps, new_term)

        assert len(new_term.main_preps) == self.main_prep_count
        assert len(new_term.sub_preps) == self.sub_prep_count - 7
        assert new_preps.size(active_prep_only=True) == old_preps.size(active_prep_only=True) - 9
        assert new_preps.size() == old_preps.size()
