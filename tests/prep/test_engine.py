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
import unittest
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.block import Block
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.icon_constant import PRepGrade, IconScoreContextType
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


class TestEngine(unittest.TestCase):
    def setUp(self) -> None:
        size = 200
        total_delegated = 0

        preps = PRepContainer()

        # Create dummy preps
        for i in range(size):
            address = Address.from_prefix_and_int(AddressPrefix.EOA, i)
            delegated = icx_to_loop(1000 - i)
            total_delegated += delegated

            prep = PRep(address,
                        block_height=i,
                        delegated=delegated)
            prep.freeze()

            assert prep.grade == PRepGrade.CANDIDATE
            assert prep.delegated == delegated
            assert prep.block_height == i
            preps.add(prep)

        preps.freeze()

        prep_engine = PRepEngine()
        prep_engine.preps = preps

        IconScoreContext.engine = Mock()
        IconScoreContext.engine.prep = prep_engine
        IconScoreContext.storage = Mock()
        IconScoreContext.storage.prep = Mock()

        context = _create_context()
        context.main_prep_count = PREP_MAIN_PREPS
        context.main_and_sub_prep_count = PREP_MAIN_AND_SUB_PREPS

        self.context = context
        self.total_supply = icx_to_loop(8_046_000)
        self.total_delegated = total_delegated

    def tearDown(self) -> None:
        self.new_preps = None

    def test__update_prep_grades_1(self):
        context = self.context

        # Case0: Network has just decentralized without any delegation
        context.engine.prep._update_prep_grades_on_term_ended(context)

        for i, prep in enumerate(context.preps):
            if i < PREP_MAIN_PREPS:
                self.assertEqual(PRepGrade.MAIN, prep.grade)
            elif i < PREP_MAIN_AND_SUB_PREPS:
                self.assertEqual(PRepGrade.SUB, prep.grade)
            else:
                self.assertEqual(PRepGrade.CANDIDATE, prep.grade)

        term = _create_term(self.total_supply, self.total_delegated)
        term.set_preps(context.preps, context.main_prep_count, context.main_and_sub_prep_count)
        term.freeze()

        context.engine.prep.term = term
        context.engine.prep.preps = context.preps
        context.engine.prep.preps.freeze()

        context._preps = context.engine.prep.preps.copy(mutable=True)

        for i in range(100):
            prep = context.preps.get_by_index(i + context.main_and_sub_prep_count)
            dirty_prep = prep.copy()
            dirty_prep.delegated = icx_to_loop(5000) - i
            context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

        context.engine.prep._update_prep_grades_on_term_ended(context)

        for i, prep in enumerate(context.preps):
            if i < PREP_MAIN_PREPS:
                assert prep.grade == PRepGrade.MAIN
                assert prep.delegated == icx_to_loop(5000) - i
            elif i < PREP_MAIN_AND_SUB_PREPS:
                self.assertEqual(PRepGrade.SUB, prep.grade)
                assert prep.delegated == icx_to_loop(5000) - i
            else:
                self.assertEqual(PRepGrade.CANDIDATE, prep.grade)
                assert prep.delegated == icx_to_loop(1000 - i + context.main_and_sub_prep_count)

        for i, prep_snapshot in enumerate(term.preps):
            prep = context.preps.get_by_index(i + context.main_and_sub_prep_count)
            assert prep_snapshot.address == prep.address
