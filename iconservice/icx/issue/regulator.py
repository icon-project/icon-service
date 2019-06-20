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

from typing import Optional, Tuple

from .storage import RegulatorVariable
from ...icon_constant import I_SCORE_EXCHANGE_RATE
from ...iconscore.icon_score_context import IconScoreContext


# todo: implement fee related logic
class Regulator:
    def __init__(self):
        self._regulator_variable: 'RegulatorVariable' = None

        self._deducted_icx = None
        self._corrected_icx_issue_amount = None

    @property
    def deducted_icx(self):
        return self._deducted_icx

    @property
    def remain_over_issued_icx(self):
        return self._regulator_variable.over_issued_i_score // I_SCORE_EXCHANGE_RATE

    @property
    def corrected_icx_issue_amount(self):
        return self._corrected_icx_issue_amount

    def set_issue_info_about_correction(self, context: 'IconScoreContext', issue_amount):
        self._regulator_variable: 'RegulatorVariable' = context.storage.issue.get_regulator_variable(context)
        calc_next_block_height = context.storage.iiss.get_calc_next_block_height(context)

        current_calc_period_total_issued_icx: int = self._regulator_variable.current_calc_period_issued_icx
        current_calc_period_total_issued_icx += issue_amount
        if calc_next_block_height == context.block.height:
            i_score = context.storage.rc.get_prev_calc_period_issued_i_score()
            deducted_icx, remain_over_issued_i_score, corrected_icx_issue_amount = \
                self._correct_issue_amount_on_calc_period(i_score, issue_amount)

            self._regulator_variable.prev_calc_period_issued_icx = current_calc_period_total_issued_icx
            self._regulator_variable.current_calc_period_issued_icx = 0
        else:
            deducted_icx, remain_over_issued_i_score, corrected_icx_issue_amount = \
                self._correct_issue_amount(issue_amount)

            self._regulator_variable.current_calc_period_issued_icx = current_calc_period_total_issued_icx
        self._regulator_variable.over_issued_i_score = remain_over_issued_i_score
        self._deducted_icx, self._corrected_icx_issue_amount = deducted_icx, corrected_icx_issue_amount

    def put_regulate_variable(self, context: 'IconScoreContext'):
        context.storage.issue.put_regulator_variable(context, self._regulator_variable)

    @staticmethod
    def _reflect_difference_in_issuing(icx_issue_amount: int, over_issued_icx: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        corrected_icx_issue_amount = icx_issue_amount - over_issued_icx
        if over_issued_icx < 0:
            deducted_icx = over_issued_icx
            remain_over_issued_icx = 0
            return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount

        if corrected_icx_issue_amount >= 0:
            remain_over_issued_icx = 0
            deducted_icx = over_issued_icx
        else:
            remain_over_issued_icx = abs(corrected_icx_issue_amount)
            corrected_icx_issue_amount = 0
            deducted_icx = icx_issue_amount

        return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount

    @staticmethod
    def _separate_icx_and_i_score(i_score: int) -> Tuple[int, int]:
        abs_i_score = abs(i_score)
        over_issued_icx = abs_i_score // I_SCORE_EXCHANGE_RATE
        over_issued_i_score = abs_i_score % I_SCORE_EXCHANGE_RATE
        if i_score < 0:
            over_issued_icx = -over_issued_icx
            over_issued_i_score = -over_issued_i_score

        return over_issued_icx, over_issued_i_score

    @staticmethod
    def _is_data_suitable_to_process_issue_correction(prev_calc_period_issued_i_score: Optional[int]):
        return prev_calc_period_issued_i_score is not None

    def _correct_issue_amount_on_calc_period(self,
                                             prev_calc_period_issued_i_score: Optional[int],
                                             icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        prev_calc_period_issued_icx: Optional[int] = self._regulator_variable.prev_calc_period_issued_icx
        remain_over_issued_i_score: int = self._regulator_variable.over_issued_i_score

        if not self._is_data_suitable_to_process_issue_correction(prev_calc_period_issued_i_score):
            raise AssertionError("There is no prev_calc_period_i_score")

        # get difference between icon_service and reward_calc after set exchange rates
        prev_calc_over_issued_i_score: int = \
            prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score
        total_over_issued_i_score: int = prev_calc_over_issued_i_score + remain_over_issued_i_score
        over_issued_icx, over_issued_i_score = self._separate_icx_and_i_score(total_over_issued_i_score)

        deducted_icx, remain_over_issued_icx, icx_issue_amount = \
            self._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

        remain_over_issued_i_score = remain_over_issued_icx * I_SCORE_EXCHANGE_RATE + over_issued_i_score

        # deducted_icx can be negative value (in case of reward calculator having been issued more)
        return deducted_icx, remain_over_issued_i_score, icx_issue_amount

    def _correct_issue_amount(self, icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        remain_over_issued_i_score: int = self._regulator_variable.over_issued_i_score
        remain_over_issued_icx: int = 0
        deducted_icx: int = 0

        if remain_over_issued_i_score > 0:
            remain_over_issued_icx = remain_over_issued_i_score // I_SCORE_EXCHANGE_RATE

        if remain_over_issued_icx > 0:
            deducted_icx, remain_over_issued_icx, icx_issue_amount = \
                self._reflect_difference_in_issuing(icx_issue_amount, remain_over_issued_icx)
            remain_over_issued_i_score -= deducted_icx * I_SCORE_EXCHANGE_RATE

        return deducted_icx, remain_over_issued_i_score, icx_issue_amount
