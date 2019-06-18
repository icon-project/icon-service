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

    @classmethod
    def _reflect_difference_in_issuing(cls, icx_issue_amount: int, over_issued_icx: int) -> Tuple[int, int, int]:
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

    @classmethod
    def _separate_icx_and_i_score(cls, i_score: int) -> Tuple[int, int]:
        abs_i_score = abs(i_score)
        over_issued_icx = abs_i_score // I_SCORE_EXCHANGE_RATE
        over_issued_i_score = abs_i_score % I_SCORE_EXCHANGE_RATE
        if i_score < 0:
            over_issued_icx = -over_issued_icx
            over_issued_i_score = -over_issued_i_score

        return over_issued_icx, over_issued_i_score

    @classmethod
    def _is_data_suitable_to_process_issue_correction(cls, prev_calc_period_issued_i_score: Optional[int],
                                                      prev_calc_period_issued_icx: Optional[int]):
        return (prev_calc_period_issued_i_score is None and prev_calc_period_issued_icx is not None) or \
               (prev_calc_period_issued_i_score is not None and prev_calc_period_issued_icx is None)

    @classmethod
    def _is_first_calculate_period(cls, prev_calc_period_issued_i_score: Optional[int],
                                   prev_calc_period_issued_icx: Optional[int]):
        # in case of first calculate period
        # (i.e. both prev_calc_period_issued_i_score and prev_calc_period_issued_icx is None), skip the correction logic
        return prev_calc_period_issued_i_score is None and prev_calc_period_issued_icx is None

    # todo: get type (calculate, invoke) and input data to db
    @classmethod
    def correct_issue_amount_on_calc_period(cls,
                                            context: 'IconScoreContext',
                                            prev_calc_period_issued_i_score: Optional[int],
                                            icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        # db get
        regulator_variable: 'RegulatorVariable' = context.storage.issue.get_regulator_variable(context)
        current_calc_period_total_issued_icx: int = regulator_variable.current_calc_period_issued_icx
        prev_calc_period_issued_icx: Optional[int] = regulator_variable.prev_calc_period_issued_icx
        remain_over_issued_i_score: int = regulator_variable.over_issued_i_score

        remain_over_issued_icx = 0
        deducted_icx = 0

        # 확인로직(적절한가??)
        if not cls._is_data_suitable_to_process_issue_correction(prev_calc_period_issued_i_score,
                                                                 prev_calc_period_issued_icx):
            raise AssertionError("There is no prev_calc_period_i_score or "
                                 "prev_calc_period_issued_icx data even though on calc period")

        current_calc_period_total_issued_icx += icx_issue_amount
        if not cls._is_first_calculate_period(prev_calc_period_issued_i_score, prev_calc_period_issued_icx):
            # get difference between icon_service and reward_calc after set exchange rates
            prev_calc_over_issued_i_score: int = \
                prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score
            total_over_issued_i_score: int = prev_calc_over_issued_i_score + remain_over_issued_i_score
            over_issued_icx, over_issued_i_score = cls._separate_icx_and_i_score(total_over_issued_i_score)

            deducted_icx, remain_over_issued_icx, icx_issue_amount = \
                cls._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

            remain_over_issued_i_score = remain_over_issued_icx * I_SCORE_EXCHANGE_RATE + over_issued_i_score
            regulator_variable.over_issued_i_score = remain_over_issued_i_score

        regulator_variable.prev_calc_period_issued_icx = current_calc_period_total_issued_icx
        regulator_variable.current_calc_period_issued_icx = 0

        context.storage.issue.put_regulator_variable(context, regulator_variable)

        # deducted_icx can be negative value (in case of reward calculator having been issued more)
        return deducted_icx, remain_over_issued_icx, icx_issue_amount

    @classmethod
    def correct_issue_amount(cls, context: 'IconScoreContext', icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        regulator_variable: 'RegulatorVariable' = context.storage.issue.get_regulator_variable(context)
        current_calc_period_total_issued_icx: int = regulator_variable.current_calc_period_issued_icx
        remain_over_issued_i_score: int = regulator_variable.over_issued_i_score
        remain_over_issued_icx: int = 0
        deducted_icx: int = 0

        if remain_over_issued_i_score > 0:
            remain_over_issued_icx = remain_over_issued_i_score // I_SCORE_EXCHANGE_RATE
        current_calc_period_total_issued_icx += icx_issue_amount

        if remain_over_issued_icx > 0:
            deducted_icx, remain_over_issued_icx, icx_issue_amount = \
                cls._reflect_difference_in_issuing(icx_issue_amount, remain_over_issued_icx)
            remain_over_issued_i_score -= deducted_icx * I_SCORE_EXCHANGE_RATE
            regulator_variable.over_issued_i_score = remain_over_issued_i_score
        regulator_variable.current_calc_period_issued_icx = current_calc_period_total_issued_icx
        context.storage.issue.put_regulator_variable(context, regulator_variable)

        return deducted_icx, remain_over_issued_icx, icx_issue_amount
