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

from typing import TYPE_CHECKING

from iconcommons import Logger
from ...icon_constant import IISS_MAX_REWARD_RATE, IISS_ANNUAL_BLOCK, IISS_MONTH, IISS_LOG_TAG, PERCENTAGE_FOR_BETA_2

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext


class IssueFormula(object):

    def __init__(self, main_prep_count: int):
        self._handler: dict = {
            'prep': self._handle_icx_issue_formula_for_prep
        }
        # todo: in case of issuing from IISS_REV, get from the storage (not constant value)
        self.main_prep_count: int = main_prep_count

    def calculate(self, context: 'IconScoreContext', group: str, data: dict) -> int:
        handler = self._handler[group]
        # todo: as field name changed, this handler pattern not efficient. change the logic
        value = handler(context=context,
                        irep=data["irep"],
                        rrep=data["rrep"],
                        total_delegation=data["totalDelegation"])
        return value

    @staticmethod
    def calculate_rrep(rmin: int, rmax: int, rpoint: int, total_supply: int, total_delegated: int) -> int:
        stake_percentage: float = total_delegated / total_supply * IISS_MAX_REWARD_RATE
        if stake_percentage >= rpoint:
            return rmin

        first_operand: float = (rmax - rmin) / (rpoint ** 2)
        second_operand: float = (stake_percentage - rpoint) ** 2
        return int(first_operand * second_operand + rmin)

    @staticmethod
    def calculate_irep_per_block_contributor(irep: int) -> int:
        return int(irep * IISS_MONTH // (IISS_ANNUAL_BLOCK * 2))

    def _handle_icx_issue_formula_for_prep(self,
                                           context: 'IconScoreContext',
                                           irep: int,
                                           rrep: int,
                                           total_delegation: int) -> int:
        calculated_irep: int = self.calculate_irep_per_block_contributor(irep)
        beta_1: int = 0
        beta_2: int = 0
        if context.is_decentralized():
            beta_1: int = calculated_irep * self.main_prep_count
            beta_2: int = calculated_irep * PERCENTAGE_FOR_BETA_2 if context.term.total_delegated > 0 else 0

        temp_rrep = IssueFormula.calculate_temporary_reward_prep(rrep)
        beta_3: int = temp_rrep * total_delegation // (IISS_ANNUAL_BLOCK * IISS_MAX_REWARD_RATE)
        Logger.info("Calculated issue amount about this block. "
                    f"calculated_irep: {calculated_irep} irep: {irep} rrep: {temp_rrep} "
                    f"total_delegation: {total_delegation} "
                    f"beta1: {beta_1} beta2: {beta_2} beta3: {beta_3}", IISS_LOG_TAG)
        return beta_1 + beta_2 + beta_3

    @staticmethod
    def calculate_temporary_reward_prep(rrep: int) -> int:
        # todo: after eep and dapp is added, do not multiple 3 to beta3
        return rrep * 3
