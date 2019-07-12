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

from ...icon_constant import IISS_MAX_REWARD_RATE, IISS_ANNUAL_BLOCK, IISS_MONTH, \
    PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS


class IssueFormula(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, IssueFormula):
            cls._instance = super().__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self,
                 prep_count: int = PREP_MAIN_PREPS,
                 sub_prep_count: int = PREP_MAIN_AND_SUB_PREPS):
        self._handler: dict = {
            'prep': self._handle_icx_issue_formula_for_prep
        }
        # todo: in case of issuing from IISS_REV, get from the storage (not constant value)
        self._prep_count: int = prep_count
        # todo: in case of issuing from IISS_REV, get from the storage (not constant value)
        self._sub_prep_count: int = sub_prep_count

    def calculate(self, group: str, data: dict) -> int:
        handler = self._handler[group]
        # todo: as field name changed, this handler pattern not efficient. change the logic
        value = handler(irep=data["irep"],
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

    def _handle_icx_issue_formula_for_prep(self, irep: int, rrep: int, total_delegation: int) -> int:
        calculated_irep: int = self.calculate_irep_per_block_contributor(irep)
        beta_1: int = calculated_irep * self._prep_count
        beta_2: int = calculated_irep * self._sub_prep_count
        beta_3: int = rrep * total_delegation // (IISS_ANNUAL_BLOCK * IISS_MAX_REWARD_RATE)
        return beta_1 + beta_2 + beta_3

    def get_limit_inflation_beta(self, irep: int) -> int:
        calculated_irep: int = self.calculate_irep_per_block_contributor(irep)
        beta_1: int = calculated_irep * self._prep_count
        beta_2: int = calculated_irep * self._sub_prep_count
        return beta_1 + beta_2
