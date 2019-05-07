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


class IcxIssueFormula(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    def __init__(self,
                 prep_count: int = 22,
                 sub_prep_count: int = 100):
        self._handler = {'prep': self._handle_icx_issue_formula_for_prep,
                         'eep': self._handle_icx_issue_formula_for_eep,
                         'dapp': self._handle_icx_issue_formula_for_dapp}
        self._prep_count: int = prep_count
        self._sub_prep_count: int = sub_prep_count

    def calculate(self, group: str, data: dict) -> int:
        handler = self._handler[group]
        value = handler(data)
        return value

    @staticmethod
    def calculate_r_rep(r_min, r_max, l_point, total_supply, total_delegated):
        stake_percentage = int(total_delegated / total_supply * IISS_MAX_REWARD_RATE)

        left = (r_max - r_min) / pow(l_point, 2)
        right = pow(stake_percentage - l_point, 2)

        return int(left * right + r_min)

    @staticmethod
    def calculate_i_rep_per_block_contributor(i_rep):
        return int(i_rep * 0.5 * IISS_MONTH / IISS_ANNUAL_BLOCK)

    def _handle_icx_issue_formula_for_prep(self, data: dict) -> int:
        calculated_i_rep = self.calculate_i_rep_per_block_contributor(data["incentive"])
        beta_1 = calculated_i_rep * self._prep_count
        beta_2 = calculated_i_rep * self._sub_prep_count
        beta_3 = data["rewardRate"] * data["totalDelegation"] // IISS_ANNUAL_BLOCK
        return beta_1 + beta_2 + beta_3

    @staticmethod
    def _handle_icx_issue_formula_for_eep(data: dict) -> int:
        return 2

    @staticmethod
    def _handle_icx_issue_formula_for_dapp(data: dict) -> int:
        return 3
