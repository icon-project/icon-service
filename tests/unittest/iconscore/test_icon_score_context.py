# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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

import random
import unittest
from unittest.mock import Mock

import pytest

from iconservice.icon_constant import IconScoreContextType, PRepFlag, TermFlag, Revision, PRepGrade, PenaltyReason, \
    PRepStatus, IconNetworkValueType
from iconservice.icon_network.data.value import *
from iconservice.icon_network import INVContainer, INVEngine
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextFactory
from iconservice.prep.data import Term, PRep
from iconservice.prep.data.prep_container import PRepContainer
from iconservice.prep.engine import Engine as PRepEngine
from iconservice.utils import icx_to_loop, ContextEngine
from tests.legacy_unittest import utils

MAIN_PREPS = 22
ELECTED_PREPS = 100
TOTAL_PREPS = 110
TERM_PERIOD = 43120


def _impose_penalty_on_prep(prep: 'PRep', penalty: 'PenaltyReason'):
    assert not prep.is_frozen()

    prep.penalty = penalty
    prep.grade = PRepGrade.CANDIDATE
    prep.status = PRepStatus.ACTIVE if penalty == PenaltyReason.BLOCK_VALIDATION else PRepStatus.DISQUALIFIED


@pytest.fixture(scope="module")
def settable_inv_container():
    default_service_config: int = 0
    default_step_costs = {
        'default': 1_000_000,
        'contractCall': 15_000,
        'contractCreate': 200_000,
        'contractUpdate': 80_000,
        'contractDestruct': -70_000,
        'contractSet': 30_000,
        'get': 0,
        'set': 200,
        'replace': 50,
        'delete': -150,
        'input': 200,
        'eventLog': 100,
        'apiCall': 0
    }
    default_max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    default_step_price: int = 0
    default_score_black_list: list = []
    default_import_white_list = {"iconservice": ['*']}
    inv_container = INVContainer(is_migrated=False)
    inv_container._icon_network_values = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(0),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(default_score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(default_step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(default_step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(default_max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(default_service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(default_import_white_list)
    }
    return inv_container


@pytest.fixture
def prep_engine():
    preps = utils.create_dummy_preps(size=TOTAL_PREPS, main_preps=MAIN_PREPS, elected_preps=ELECTED_PREPS)
    preps.freeze()
    assert preps.is_frozen()
    assert not preps.is_dirty()

    term = Term(sequence=0,
                start_block_height=100,
                period=TERM_PERIOD,
                irep=icx_to_loop(50000),
                total_supply=preps.total_delegated,
                total_delegated=preps.total_delegated)
    term.set_preps(preps, MAIN_PREPS, ELECTED_PREPS)
    term.freeze()
    assert term.is_frozen()
    assert not term.is_dirty()

    prep_engine = PRepEngine()
    prep_engine.preps = preps
    prep_engine.term = term

    return prep_engine


@pytest.fixture
def context_factory(settable_inv_container: 'INVContainer', prep_engine: 'PRepEngine'):
    inv_engine = INVEngine()
    settable_inv_container.set_by_icon_service(RevisionCode(Revision.REALTIME_P2P_ENDPOINT_UPDATE.value))
    inv_engine._inv_container = settable_inv_container

    IconScoreContext.engine = ContextEngine(prep=prep_engine, inv=inv_engine)
    IconScoreContext.storage = Mock()
    context_factory = IconScoreContextFactory()
    return context_factory


class TestIconScoreContext:

    def test_update_dirty_prep_batch_with_p2p_endpoint_changed_main_prep(self, prep_engine, context_factory):
        old_preps: 'PRepContainer' = prep_engine.preps
        old_term: 'Term' = prep_engine.term

        block = utils.create_dummy_block()
        context: 'IconScoreContext' = context_factory.create(IconScoreContextType.INVOKE, block)
        self._check_initial_context(context)

        # Case 1: the p2p_endpoint of a main P-Rep is changed
        index = random.randint(0, MAIN_PREPS - 1)
        dirty_prep: 'PRep' = old_preps.get_by_index(index).copy()
        dirty_prep.set(p2p_endpoint=f"new_address_{index}:1234")
        assert dirty_prep.is_dirty()
        assert dirty_prep.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_prep.grade == PRepGrade.MAIN
        context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

        # Check whether set TermFlag.MAIN_PREP_P2P_ENDPOINT to context.term.flags
        # No change in main and sub P-Rep list of term
        assert id(context.term) != id(old_term)
        assert not context.term.is_frozen()
        assert context.term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert context.term.main_preps == old_term.main_preps
        assert context.term.sub_preps == old_term.sub_preps

        # Check for context.preps attributes
        assert id(context.preps) != id(old_preps)
        assert not context.preps.is_frozen()
        assert context.preps.is_dirty()
        assert context.preps.get_by_index(index) == dirty_prep

        # Check the changed P-Rep
        old_prep = old_preps.get_by_index(index)
        new_prep = context.preps.get_by_index(index)

        assert new_prep == dirty_prep
        assert new_prep != old_prep
        assert dirty_prep.address == new_prep.address == old_prep.address

    def test_update_dirty_prep_batch_with_p2p_endpoint_changed_sub_prep_and_candidate(self, prep_engine, context_factory):
        old_preps: 'PRepContainer' = prep_engine.preps
        old_term: 'Term' = prep_engine.term

        block = utils.create_dummy_block()
        context: 'IconScoreContext' = context_factory.create(IconScoreContextType.INVOKE, block)
        self._check_initial_context(context)

        # the p2p_endpoint of a sub P-Rep is changed
        sub_index = random.randint(MAIN_PREPS, ELECTED_PREPS - 1)
        dirty_sub_prep: 'PRep' = old_preps.get_by_index(sub_index).copy()
        dirty_sub_prep.set(p2p_endpoint=f"new_address_{sub_index}:1234")
        assert dirty_sub_prep.is_dirty()
        assert dirty_sub_prep.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_sub_prep.grade == PRepGrade.SUB
        context.put_dirty_prep(dirty_sub_prep)

        # the p2p_endpoint of a P-Rep candidate is changed
        candidate_index = random.randint(ELECTED_PREPS, old_preps.size(active_prep_only=True) - 1)
        dirty_prep_candidate: 'PRep' = old_preps.get_by_index(candidate_index).copy()
        dirty_prep_candidate.set(p2p_endpoint=f"new_address_{candidate_index}:1234")
        assert dirty_prep_candidate.is_dirty()
        assert dirty_prep_candidate.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_prep_candidate.grade == PRepGrade.CANDIDATE
        context.put_dirty_prep(dirty_prep_candidate)

        context.update_dirty_prep_batch()

        # Check for term attributes
        # No change to term
        assert id(context.term) == id(old_term)
        assert context.term.is_frozen()
        assert not context.term.is_dirty()

        # Check for preps attributes
        assert id(context.preps) != id(old_preps)
        assert not context.preps.is_frozen()
        assert context.preps.is_dirty()
        assert context.preps.get_by_index(sub_index) == dirty_sub_prep
        assert context.preps.get_by_index(candidate_index) == dirty_prep_candidate

    def test_update_dirty_prep_batch_with_penalized_main_prep(self, prep_engine, context_factory):
        block = utils.create_dummy_block()
        context: 'IconScoreContext' = context_factory.create(IconScoreContextType.INVOKE, block)
        self._check_initial_context(context)

        penalties = [
            PenaltyReason.LOW_PRODUCTIVITY,
            PenaltyReason.PREP_DISQUALIFICATION,
            PenaltyReason.BLOCK_VALIDATION
        ]

        sub_prep_count = ELECTED_PREPS - MAIN_PREPS

        # Check for 3 penalties
        for i, penalty in enumerate(penalties):
            # Choose a main P-Rep
            address = context.term.main_preps[i].address

            # Duplicate a main P-Rep indicated by address to dirty_prep
            dirty_prep: 'PRep' = context.get_prep(address, mutable=True)
            assert dirty_prep.address == address
            assert dirty_prep.grade == PRepGrade.MAIN
            assert not dirty_prep.is_frozen()
            assert not dirty_prep.is_dirty()

            # Impose low productivity penalty on the main P-Rep chosen above
            _impose_penalty_on_prep(dirty_prep, penalty)
            assert dirty_prep.is_flags_on(PRepFlag.GRADE | PRepFlag.PENALTY)
            assert dirty_prep.is_flags_on(PRepFlag.STATUS) == (penalty != PenaltyReason.BLOCK_VALIDATION)

            context.put_dirty_prep(dirty_prep)
            context.update_dirty_prep_batch()

            # context.preps and context.term should be mutable and dirty
            # because main P-Rep substitution happened by penalty
            assert not context.preps.is_frozen()
            assert not context.term.is_frozen()
            assert context.preps.is_dirty()
            assert context.term.is_dirty()

            # The penalized main P-Rep should be replaced with the first sub P-Rep
            assert not context.term.is_main_prep(dirty_prep.address)
            assert len(context.term.main_preps) == MAIN_PREPS
            assert len(context.term.sub_preps) == sub_prep_count - 1
            sub_prep_count -= 1

            assert id(dirty_prep) == id(context.preps.get_by_address(address))

            address = context.term.main_preps[i].address
            new_main_prep: 'PRep' = context.preps.get_by_address(address)

            # The grade update for a new main P-Rep will be batched
            # in iconservice.prep.engine.Engine._update_prep_grades()
            assert new_main_prep.grade == PRepGrade.SUB
            assert not new_main_prep.is_dirty()

    def test_update_dirty_prep_batch_by_elected_prep_unregistration(self, prep_engine, context_factory):
        items = [
            (random.randint(0, MAIN_PREPS - 1), PRepGrade.MAIN),
            (random.randint(MAIN_PREPS, ELECTED_PREPS - 1), PRepGrade.SUB),
        ]

        for index, grade in items:
            block = utils.create_dummy_block()
            context: 'IconScoreContext' = context_factory.create(IconScoreContextType.INVOKE, block)
            self._check_initial_context(context)

            prep: 'PRep' = context.preps.get_by_index(index)
            assert prep.grade == grade

            # Duplicate the P-Rep specified by address to dirty_prep
            dirty_prep = context.get_prep(prep.address, mutable=True)
            assert dirty_prep.address == prep.address
            assert dirty_prep.grade == grade
            assert not dirty_prep.is_frozen()
            assert not dirty_prep.is_dirty()

            # Unregister the P-Rep
            dirty_prep.status = PRepStatus.UNREGISTERED
            dirty_prep.grade = PRepGrade.CANDIDATE
            dirty_prep.penalty = PenaltyReason.NONE
            # The status and grade of the P-Rep are changed
            assert dirty_prep.is_flags_on(PRepFlag.STATUS | PRepFlag.GRADE)
            # The penalty of the P-Rep is not changed
            assert not dirty_prep.is_flags_on(PRepFlag.PENALTY)

            context.put_dirty_prep(dirty_prep)
            context.update_dirty_prep_batch()

            # context.preps and context.term should be mutable and dirty
            assert not context.preps.is_frozen()
            assert not context.term.is_frozen()
            assert context.preps.is_dirty()
            assert context.term.is_dirty()

            assert dirty_prep.address not in context.term
            assert dirty_prep == context.preps.get_by_address(dirty_prep.address)

    def test_update_dirty_prep_batch_by_prep_candidate_unregistration(self, prep_engine, context_factory):
        for i in range(3):
            index = ELECTED_PREPS + i
            grade = PRepGrade.CANDIDATE

            block = utils.create_dummy_block()
            context: 'IconScoreContext' = context_factory.create(IconScoreContextType.INVOKE, block)
            self._check_initial_context(context)

            old_active_prep_count: int = context.preps.size(active_prep_only=True)
            old_total_prep_count: int = context.preps.size(active_prep_only=False)  # active + inactive
            # There is no inactive P-Rep at this moment
            assert old_active_prep_count == old_total_prep_count

            prep: 'PRep' = context.preps.get_by_index(index)
            assert prep.grade == grade

            # Duplicate the P-Rep specified by address to dirty_prep
            dirty_prep = context.get_prep(prep.address, mutable=True)
            assert dirty_prep.address == prep.address
            assert dirty_prep.grade == grade
            assert not dirty_prep.is_frozen()
            assert not dirty_prep.is_dirty()

            # Unregister the P-Rep
            dirty_prep.status = PRepStatus.UNREGISTERED
            dirty_prep.grade = PRepGrade.CANDIDATE
            dirty_prep.penalty = PenaltyReason.NONE
            # The status of the P-Rep is changed
            assert dirty_prep.is_flags_on(PRepFlag.STATUS)
            # The penalty and grade of the P-Rep are not changed
            assert not dirty_prep.is_flags_on(PRepFlag.PENALTY | PRepFlag.GRADE)

            # A P-Rep candidate unregistration will be applied to context
            context.put_dirty_prep(dirty_prep)
            context.update_dirty_prep_batch()

            # context.preps should become mutable and dirty
            assert not context.preps.is_frozen()
            assert context.preps.is_dirty()

            # As the unregistered P-Rep is not an elected P-Rep, nothing happens to context.term
            assert context.term.is_frozen()
            assert not context.term.is_dirty()

            # A P-Rep candidate unregistration do not affect context.term
            assert dirty_prep.address not in context.term
            assert dirty_prep == context.preps.get_by_address(dirty_prep.address)

            # The number of active P-Reps will be decreased by one compared to the previous one
            assert context.preps.size(active_prep_only=True) == old_active_prep_count - 1
            assert context.preps.size(active_prep_only=False) == old_total_prep_count

    @staticmethod
    def _check_initial_context(context: 'IconScoreContext'):
        assert context.revision >= Revision.REALTIME_P2P_ENDPOINT_UPDATE.value

        assert isinstance(context.preps, PRepContainer)
        assert not context.preps.is_frozen()
        assert not context.preps.is_dirty()

        assert isinstance(context.term, Term)
        assert context.term.is_frozen()
        assert not context.term.is_dirty()
