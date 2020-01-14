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

from iconservice.icon_constant import IconScoreContextType, PRepFlag, TermFlag, Revision, PRepGrade
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextFactory
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.prep.data import Term, PRep
from iconservice.prep.data.prep_container import PRepContainer
from iconservice.prep.engine import Engine as PRepEngine
from iconservice.utils import icx_to_loop
from .. import utils


class TestIconScoreContext(unittest.TestCase):
    MAIN_PREPS = 22
    ELECTED_PREPS = 100
    TERM_PERIOD = 43120

    def setUp(self) -> None:
        IconScoreContext.engine = Mock()
        IconScoreContext.storage = Mock()

        preps = utils.create_dummy_preps(
            size=self.ELECTED_PREPS + 10, main_preps=self.MAIN_PREPS, elected_preps=self.ELECTED_PREPS)
        preps.freeze()
        assert preps.is_frozen()
        assert not preps.is_dirty()

        term = Term(sequence=0,
                    start_block_height=100,
                    period=self.TERM_PERIOD,
                    irep=icx_to_loop(50000),
                    total_supply=preps.total_delegated,
                    total_delegated=preps.total_delegated)
        term.set_preps(preps, self.MAIN_PREPS, self.ELECTED_PREPS)
        term.freeze()
        assert term.is_frozen()
        assert not term.is_dirty()

        prep_engine = PRepEngine()
        prep_engine.preps = preps
        prep_engine.term = term

        IconScoreContext.engine.prep = prep_engine

        step_counter_factory = IconScoreStepCounterFactory()
        context_factory = IconScoreContextFactory(step_counter_factory)

        self.context_factory = context_factory
        self.preps = preps
        self.term = term

    def test_update_dirty_prep_batch_with_p2p_endpoint_changed_main_prep(self):
        old_preps: 'PRepContainer' = self.preps
        old_term: 'Term' = self.term

        block = utils.create_dummy_block()
        context: 'IconScoreContext' = self.context_factory.create(IconScoreContextType.INVOKE, block)
        context.revision = Revision.REALTIME_P2P_ENDPOINT_UPDATE.value
        assert isinstance(context.preps, PRepContainer)

        # Case 1: the p2p_endpoint of a main P-Rep is changed
        index = random.randint(0, self.MAIN_PREPS - 1)
        dirty_prep: 'PRep' = old_preps.get_by_index(index).copy()
        dirty_prep.set(p2p_endpoint=f"new_address_{index}:1234")
        assert dirty_prep.is_dirty()
        assert dirty_prep.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_prep.grade == PRepGrade.MAIN
        context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

        assert id(context.term) != id(old_term)
        assert not context.term.is_frozen()
        assert context.term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert len(context.term.main_preps) == len(old_term.main_preps)
        assert context.term.sub_preps == old_term.sub_preps

        # Check for preps attributes
        assert id(context.preps) != id(old_preps)
        assert not context.preps.is_frozen()
        assert context.preps.is_dirty()
        assert context.preps.get_by_index(index) == dirty_prep

        # Check for the changed P-Rep
        old_prep = old_preps.get_by_index(index)
        new_prep = context.preps.get_by_index(index)

        assert new_prep == dirty_prep
        assert new_prep != old_prep
        assert dirty_prep.address == new_prep.address == old_prep.address

    def test_update_dirty_prep_batch_with_p2p_endpoint_changed_sub_prep_and_candidate(self):
        old_preps: 'PRepContainer' = self.preps
        old_term: 'Term' = self.term

        block = utils.create_dummy_block()
        context: 'IconScoreContext' = self.context_factory.create(IconScoreContextType.INVOKE, block)
        context.revision = Revision.REALTIME_P2P_ENDPOINT_UPDATE.value
        assert isinstance(context.preps, PRepContainer)

        assert id(context.preps) == id(old_preps)
        assert id(context.term) == id(old_term)

        # Case the p2p_endpoint of a sub P-Rep is changed
        sub_index = random.randint(self.MAIN_PREPS, self.ELECTED_PREPS - 1)
        dirty_sub_prep: 'PRep' = old_preps.get_by_index(sub_index).copy()
        dirty_sub_prep.set(p2p_endpoint=f"new_address_{sub_index}:1234")
        assert dirty_sub_prep.is_dirty()
        assert dirty_sub_prep.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_sub_prep.grade == PRepGrade.SUB
        context.put_dirty_prep(dirty_sub_prep)

        candidate_index = random.randint(self.ELECTED_PREPS, old_preps.size(active_prep_only=True) - 1)
        dirty_prep_candidate: 'PRep' = old_preps.get_by_index(candidate_index).copy()
        dirty_prep_candidate.set(p2p_endpoint=f"new_address_{candidate_index}:1234")
        assert dirty_prep_candidate.is_dirty()
        assert dirty_prep_candidate.flags == PRepFlag.P2P_ENDPOINT
        assert dirty_prep_candidate.grade == PRepGrade.CANDIDATE
        context.put_dirty_prep(dirty_prep_candidate)

        context.update_dirty_prep_batch()

        # Check for term attributes
        assert id(context.term) != id(old_term)
        assert not context.term.is_frozen()
        assert not context.term.flags & TermFlag.MAIN_PREP_P2P_ENDPOINT
        assert len(context.term.main_preps) == len(old_term.main_preps)
        assert context.term.sub_preps == old_term.sub_preps

        # Check for preps attributes
        assert id(context.preps) != id(old_preps)
        assert not context.preps.is_frozen()
        assert context.preps.is_dirty()
        assert context.preps.get_by_index(sub_index) == dirty_sub_prep
        assert context.preps.get_by_index(candidate_index) == dirty_prep_candidate
