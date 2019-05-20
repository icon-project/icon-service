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

from ..icon_constant import IISS_MAX_REWARD_RATE, IISS_ANNUAL_BLOCK, IISS_MONTH


class IssueFormula(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super().__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self,
                 prep_count: int = 22,
                 sub_prep_count: int = 100):
        self._handler: dict = {'prep': self._handle_icx_issue_formula_for_prep}
        self._prep_count: int = prep_count
        self._sub_prep_count: int = sub_prep_count

    def calculate(self, group: str, data: dict) -> int:
        handler = self._handler[group]
        value = handler(incentive=data["incentive"],
                        reward_rate=data["rewardRate"],
                        total_delegation=data["totalDelegation"])
        return value

    @staticmethod
    def calculate_r_rep(r_min: int, r_max: int, r_point: int, total_supply: int, total_delegated: int) -> int:
        stake_percentage: float = total_delegated / total_supply * IISS_MAX_REWARD_RATE

        first_operand: float = (r_max - r_min) / (r_point ** 2)
        second_operand: float = (stake_percentage - r_point) ** 2
        return int(first_operand * second_operand + r_min)

    @staticmethod
    def calculate_i_rep_per_block_contributor(i_rep: int) -> int:
        return int(i_rep * 0.5 * IISS_MONTH // IISS_ANNUAL_BLOCK)

    def _handle_icx_issue_formula_for_prep(self, incentive: int, reward_rate: int, total_delegation: int) -> int:
        calculated_i_rep: int = self.calculate_i_rep_per_block_contributor(incentive)
        beta_1: int = calculated_i_rep * self._prep_count
        beta_2: int = calculated_i_rep * self._sub_prep_count
        beta_3: int = int(reward_rate * total_delegation / IISS_ANNUAL_BLOCK / IISS_MAX_REWARD_RATE)
        return beta_1 + beta_2 + beta_3
