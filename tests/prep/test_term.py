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

import random
import unittest
from typing import List
from unittest.mock import Mock

from iconservice.base.address import Address, AddressPrefix
from iconservice.icon_constant import (
    PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, TERM_PERIOD, IconScoreContextType
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

        keys = "sequence", "start_block_height", "period", "irep", "total_supply", "total_delegated"

        for key in keys:
            assert getattr(self.term, key) == getattr(self, key)

        self.preps = []
        self.total_elected_prep_delegated = 0
        for i in range(PREP_MAIN_AND_SUB_PREPS):
            delegated = 100 * 10 ** 18 - i

            self.preps.append(PRep(
                Address.from_prefix_and_int(AddressPrefix.EOA, i),
                delegated=delegated
            ))
            self.total_elected_prep_delegated += delegated

    def test_set_preps(self):
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)

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

    def test_update(self):
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        assert isinstance(self.term.root_hash, bytes)
        assert len(self.term.root_hash) == 32

        # Remove an invalid Main P-Rep
        term = self.term.copy()
        invalid_elected_preps: List['Address'] = [
            self.preps[0].address,
        ]
        term.update(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS - len(invalid_elected_preps)
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash

        # Remove an invalid sub P-Rep
        term = self.term.copy()
        invalid_elected_preps: List['Address'] = [
            self.preps[PREP_MAIN_PREPS].address,
        ]
        term.update(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS - len(invalid_elected_preps)
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash == self.term.root_hash

        # Remove all sub P-Reps
        term = self.term.copy()
        invalid_elected_preps: List['Address'] = [prep.address for prep in self.preps[PREP_MAIN_PREPS:]]
        term.update(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == 0
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash == self.term.root_hash

        # Remove all main P-Reps
        term = self.term.copy()
        invalid_elected_preps: List['Address'] = [prep.address for prep in self.preps[:PREP_MAIN_PREPS]]
        term.update(invalid_elected_preps)
        assert len(term.main_preps) == PREP_MAIN_PREPS
        assert len(term.sub_preps) == PREP_MAIN_AND_SUB_PREPS - PREP_MAIN_PREPS * 2
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash

        # Remove all P-Reps except for a P-Rep
        term = self.term.copy()
        invalid_elected_preps: List['Address'] = [prep.address for prep in self.preps[1:]]
        term.update(invalid_elected_preps)
        assert len(term.main_preps) == 1
        assert len(term.sub_preps) == 0
        assert isinstance(term.root_hash, bytes)
        assert term.root_hash != self.term.root_hash

    def test_to_list_and_from_list(self):
        self.term.set_preps(self.preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        new_term = Term.from_list(self.term.to_list())

        assert id(new_term) != id(self.term)
        assert new_term.sequence == self.term.sequence
        assert new_term.start_block_height == self.term.start_block_height

        assert len(new_term.main_preps) == len(self.term.main_preps)
        assert len(new_term.sub_preps) == len(self.term.sub_preps)

        for snapshot0, snapshot1 in zip(new_term.preps, self.term.preps):
            assert snapshot0 == snapshot1

        assert isinstance(new_term.root_hash, bytes)
        assert isinstance(self.term.root_hash, bytes)
        assert new_term.root_hash == self.term.root_hash
