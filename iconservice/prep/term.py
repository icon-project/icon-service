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

from typing import TYPE_CHECKING, List, Optional

from ..base.type_converter_templates import ConstantKeys

if TYPE_CHECKING:
    from .data.candidate import Candidate
    from ..iconscore.icon_score_context import IconScoreContext
    from .data.candidate_container import CandidateContainer


class Term(object):
    """Defines P-Rep Term information
    """
    _VERSION = 0

    def __init__(self):
        self._sequence: int = -1
        self._end_block_height: int = -1
        self._period: int = -1
        self._preps: List['Candidate'] = []
        self._incentive_rep: int = -1

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def end_block_height(self) -> int:
        return self._end_block_height

    @property
    def period(self) -> int:
        return self._period

    @property
    def preps(self) -> List['Candidate']:
        return self._preps

    @property
    def incentive_rep(self) -> int:
        return self._incentive_rep

    def load(self, context: 'IconScoreContext', term_period: int, governance_variable: dict):
        data: Optional[list] = context.storage.prep.get_terms(context)
        if data:
            version = data[0]
            self._sequence = data[1]
            self._end_block_height = data[2]
            self._preps = self._make_preps(context, data[3])
            self._incentive_rep = data[4]
        else:
            self._period = term_period
            self._incentive_rep = governance_variable[ConstantKeys.INCENTIVE_REP]

    def _make_preps(self, context: 'IconScoreContext', data: list) -> List['Candidate']:
        preps: list = []
        candidate_container: 'CandidateContainer' = context.engine.prep.get_snapshot()
        for i, in range(0, len(data), 2):
            candidate: 'Candidate' = candidate_container[data[i]]
            candidate.delegated = data[i+1]
            preps.append(candidate)
        return preps

    def save(self,
             context: 'IconScoreContext',
             current_block_height: int,
             preps: List['Candidate'],
             incentive_rep: int):

        data: list = [
            self._VERSION,
            self._sequence + 1,
            current_block_height + self._period,
            self._make_prep_for_db(preps),
            incentive_rep
        ]
        context.storage.prep.put_terms(context, data)

        self._sequence += 1
        self._end_block_height = current_block_height + self._period
        self._preps = preps
        self._incentive_rep = incentive_rep

    def _make_prep_for_db(self, preps: List['Candidate']) -> list:
        data: list = []
        for prep in preps:
            data.append(prep.address)
            data.append(prep.delegated)
        return data
