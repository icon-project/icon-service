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

from ..icon_constant import PREP_MAIN_PREPS, PREP_SUB_PREPS

if TYPE_CHECKING:
    from .data.prep import PRep
    from ..iconscore.icon_score_context import IconScoreContext
    from .data.prep_container import PRepContainer


class Term(object):
    """Defines P-Rep Term information
    """
    _VERSION = 0

    def __init__(self):
        self._sequence: int = -1
        self._start_block_height: int = -1
        self._end_block_height: int = -1
        self._period: int = -1
        self._main_preps: List['PRep'] = []
        self._sub_preps: List['PRep'] = []
        self._irep: int = -1
        self._total_supply: int = -1

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def start_block_height(self) -> int:
        return self._start_block_height

    @property
    def end_block_height(self) -> int:
        return self._end_block_height

    @property
    def period(self) -> int:
        return self._period

    @property
    def main_preps(self) -> List['PRep']:
        return self._main_preps

    @property
    def sub_preps(self) -> List['PRep']:
        return self._sub_preps

    @property
    def irep(self) -> int:
        return self._irep

    @property
    def total_supply(self) -> int:
        return self._total_supply

    def load(self, context: 'IconScoreContext', term_period: int, irep: int):
        data: Optional[list] = context.storage.prep.get_term(context)
        if data:
            version = data[0]
            self._sequence = data[1]
            self._start_block_height = data[2]
            self._end_block_height = self._start_block_height + term_period - 1
            self._main_preps, self._sub_preps = self._make_preps(context, data[3])
            self._irep = data[4]
            self._total_supply = data[5]
        else:
            self._period = term_period
            self._irep = irep
            self._total_supply = context.total_supply

    def _make_preps(self, context: 'IconScoreContext', data: list) -> tuple:
        prep_list: list = []
        preps: 'PRepContainer' = context.engine.prep.get_snapshot()
        for i, in range(0, len(data), 2):
            prep: 'PRep' = preps[data[i]]
            prep.delegated = data[i + 1]
            prep_list.append(prep)

        return prep_list[:PREP_MAIN_PREPS], prep_list[PREP_MAIN_PREPS: PREP_SUB_PREPS]

    def save(self,
             context: 'IconScoreContext',
             current_block_height: int,
             preps: List['PRep'],
             irep: int,
             total_supply: int):

        data: list = [
            self._VERSION,
            self._sequence + 1,
            current_block_height + 1,
            self._make_prep_for_db(preps),
            irep,
            total_supply
        ]
        context.storage.prep.put_term(context, data)

        self._sequence += 1
        self._start_block_height = current_block_height + 1
        self._end_block_height = current_block_height + self._period
        self._main_preps = preps[:PREP_MAIN_PREPS]
        self._sub_preps = preps[PREP_MAIN_PREPS: PREP_SUB_PREPS]
        self._irep = irep
        self._total_supply = total_supply

    def _make_prep_for_db(self, preps: List['PRep']) -> list:
        data: list = []
        for prep in preps:
            data.append(prep.address)
            data.append(prep.delegated)
        return data
