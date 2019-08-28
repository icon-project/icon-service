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
from unittest.mock import Mock

from iconservice.base.address import Address
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx import IcxStorage
from iconservice.meta import MetaDBStorage
from iconservice.prep import PRepStorage
from iconservice.prep.data import PRep
from iconservice.prep.term import Term
from iconservice.utils import ContextStorage
from tests import create_address

PREPS = [PRep(Address.from_bytes(os.urandom(32))) for _ in range(PREP_MAIN_AND_SUB_PREPS)]

context = IconScoreContext(IconScoreContextType.DIRECT)
context.storage = ContextStorage(deploy=None, fee=None, icx=Mock(spec=IcxStorage), iiss=None,
                                 issue=None, rc=None, prep=Mock(spec=PRepStorage), meta=None)
context.storage.prep.put_term = Mock()


def test_save():
    current_block = random.randint(10, 100)
    # irep = random.randint(10, 100)
    total_supply = random.randint(10, 100)
    total_delegated = random.randint(10, 100)
    term_period = random.randint(10, 100)
    irep = random.randint(10, 100)

    term = Term()
    assert term.sequence == -1
    assert term.total_supply == -1
    assert term.main_preps == []
    assert term.sub_preps == []
    assert term.irep == -1
    assert term.start_block_height == -1
    assert term.end_block_height == -1
    assert term._main_prep_count == PREP_MAIN_PREPS
    assert term._main_and_sub_prep_count == PREP_MAIN_AND_SUB_PREPS
    assert term.suspended_preps == []

    for _ in range(5):
        next_sequence = term.sequence + 1
        current_block += 1
        term = term.create_next_term(next_sequence,
                                     PREP_MAIN_PREPS,
                                     PREP_MAIN_AND_SUB_PREPS,
                                     current_block,
                                     PREPS,
                                     total_supply,
                                     total_delegated,
                                     term_period,
                                     irep)
        term.save(context)
        assert term.sequence == next_sequence
        assert term.total_supply == total_supply
        assert term.main_preps == PREPS[:term._main_prep_count]
        assert term.sub_preps == PREPS[term._main_prep_count:term._main_and_sub_prep_count]
        assert term.irep == irep
        assert term.start_block_height == current_block + 1
        assert term.end_block_height == term.start_block_height + term.period - 1
        assert term.suspended_preps == []


def test_save_and_load():
    current_block = random.randint(10, 100)
    irep = random.randint(10, 100)
    total_supply = random.randint(10, 100)
    total_delegated = random.randint(10, 100)
    period = random.randint(10, 100)

    # case when term data is None
    term = Term()
    assert term.sequence == -1
    assert term.total_supply == -1
    assert term.main_preps == []
    assert term.sub_preps == []
    assert term.irep == -1
    assert term.start_block_height == -1
    assert term.end_block_height == -1
    assert term._main_prep_count == PREP_MAIN_PREPS
    assert term._main_and_sub_prep_count == PREP_MAIN_AND_SUB_PREPS

    context.storage.prep.get_term = Mock(return_value=None)
    context.storage.icx.get_total_supply = Mock(return_value=total_supply)
    term._make_main_and_sub_preps = Mock()
    term.load(context, period)
    assert term.period == period
    assert term.total_supply == total_supply
    assert term.irep == 0
    assert term.sequence == -1
    assert term.main_preps == []
    assert term.sub_preps == []
    assert term.start_block_height == -1
    assert term.end_block_height == -1
    assert term._main_prep_count == context.main_prep_count
    assert term._main_and_sub_prep_count == context.main_and_sub_prep_count

    # cases when term data is not None
    for _ in range(5):
        next_sequence = term.sequence + 1
        current_block += 1
        term._period = period
        term = Term.create_next_term(next_sequence,
                                     context.main_prep_count,
                                     context.main_and_sub_prep_count,
                                     current_block, PREPS,
                                     total_supply,
                                     total_delegated,
                                     period,
                                     irep)
        term.save(context)
        assert term.sequence == next_sequence
        assert term.total_supply == total_supply
        assert term.main_preps == PREPS[:term._main_prep_count]
        assert term.sub_preps == PREPS[term._main_prep_count:term._main_and_sub_prep_count]
        assert term.irep == irep
        assert term.start_block_height == current_block + 1
        assert term.end_block_height == term.start_block_height + term.period - 1
        assert term._main_prep_count == context.main_prep_count
        assert term._main_and_sub_prep_count == context.main_and_sub_prep_count
        saved_sequence = next_sequence

        context.storage.prep.get_term = Mock(return_value=[
            0,
            saved_sequence,
            current_block + 1,
            term._serialize_preps(PREPS),
            [],
            irep,
            total_supply,
            total_delegated
        ])
        term._make_main_and_sub_preps = Mock(return_value=PREPS)
        term.load(context, period)
        assert term.sequence == saved_sequence
        assert term.total_supply == total_supply
        assert term.main_preps == PREPS[:term._main_prep_count]
        assert term.sub_preps == PREPS[term._main_prep_count:term._main_and_sub_prep_count]
        assert term.irep == irep
        assert term.start_block_height == current_block + 1
        assert term.end_block_height == term.start_block_height + term.period - 1
        assert term._main_prep_count == context.main_prep_count
        assert term._main_and_sub_prep_count == context.main_and_sub_prep_count

