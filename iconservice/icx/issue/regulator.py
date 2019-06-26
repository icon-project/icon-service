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


class Regulator:
    def __init__(self):
        self._regulator_variable: 'RegulatorVariable' = None

        self._covered_icx_by_fee: int = None
        self._covered_icx_by_remain: int = None

        self._corrected_icx_issue_amount: int = None

    @property
    def covered_icx_by_fee(self):
        return self._covered_icx_by_fee

    @property
    def covered_icx_by_over_issue(self):
        return self._covered_icx_by_remain

    @property
    def remain_over_issued_icx(self):
        return self._regulator_variable.over_issued_i_score // I_SCORE_EXCHANGE_RATE

    @property
    def corrected_icx_issue_amount(self):
        return self._corrected_icx_issue_amount

    def set_issue_info_about_correction(self, context: 'IconScoreContext', issue_amount: int):
        regulator_variable: 'RegulatorVariable' = context.storage.issue.get_regulator_variable(context)
        prev_block_cumulative_fee = context.storage.icx.last_block.cumulative_fee
        calc_next_block_height = context.storage.iiss.get_calc_next_block_height(context)

        # update current calculated period total issued icx
        current_calc_period_total_issued_icx: int = regulator_variable.current_calc_period_issued_icx
        current_calc_period_total_issued_icx += issue_amount
        if calc_next_block_height == context.block.height:
            prev_calc_period_issued_i_score = context.storage.rc.get_prev_calc_period_issued_i_score()
            covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_i_score, corrected_icx_issue_amount = \
                self._correct_issue_amount_on_calc_period(regulator_variable.prev_calc_period_issued_icx,
                                                          prev_calc_period_issued_i_score,
                                                          regulator_variable.over_issued_i_score,
                                                          issue_amount,
                                                          prev_block_cumulative_fee)

            regulator_variable.prev_calc_period_issued_icx = current_calc_period_total_issued_icx
            regulator_variable.current_calc_period_issued_icx = 0
        else:
            covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_i_score, corrected_icx_issue_amount = \
                self._correct_issue_amount(regulator_variable.over_issued_i_score,
                                           issue_amount,
                                           prev_block_cumulative_fee)
            regulator_variable.current_calc_period_issued_icx = current_calc_period_total_issued_icx
        regulator_variable.over_issued_i_score = remain_over_issued_i_score

        self._regulator_variable = regulator_variable
        self._covered_icx_by_fee = covered_icx_by_fee
        self._covered_icx_by_remain = covered_icx_by_remain
        self._corrected_icx_issue_amount = corrected_icx_issue_amount

    def put_regulate_variable(self, context: 'IconScoreContext'):
        context.storage.issue.put_regulator_variable(context, self._regulator_variable)

    def _reflect_difference_in_issuing(self,
                                       icx_issue_amount: int,
                                       over_issued_icx: int,
                                       prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        # cover about over issued icx
        # remain_over_issued_icx, corrected_icx_issue_amount
        covered_icx_by_remain, remain_over_issued_icx, corrected_icx_issue_amount = \
            self._calculate_over_issued_icx(icx_issue_amount,
                                            over_issued_icx)

        covered_icx_by_fee, remain_over_issued_icx, corrected_icx_issue_amount = \
            self._calculate_prev_block_cumulative_fee(remain_over_issued_icx,
                                                      corrected_icx_issue_amount,
                                                      prev_block_cumulative_fee)

        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, corrected_icx_issue_amount

    @staticmethod
    def _calculate_over_issued_icx(icx_issue_amount: int,
                                   over_issued_icx: int) -> Tuple[int, int, int]:
        corrected_issue_amount = icx_issue_amount - over_issued_icx
        if over_issued_icx < 0:
            covered_icx_by_remain = over_issued_icx
            remain_over_issued_icx = 0
            return covered_icx_by_remain, remain_over_issued_icx, corrected_issue_amount

        if corrected_issue_amount >= 0:
            remain_over_issued_icx = 0
            covered_icx_by_remain = over_issued_icx
        else:
            remain_over_issued_icx = abs(corrected_issue_amount)
            corrected_issue_amount = 0
            covered_icx_by_remain = icx_issue_amount

        return covered_icx_by_remain, remain_over_issued_icx, corrected_issue_amount

    @staticmethod
    def _calculate_prev_block_cumulative_fee(remain_over_issued_icx: int,
                                             corrected_issue_amount: int,
                                             prev_block_cumulative_fee: int) -> Tuple[int, int, int]:
        corrected_issue_amount -= prev_block_cumulative_fee
        if corrected_issue_amount >= 0:
            covered_icx_by_fee = prev_block_cumulative_fee
        else:
            covered_icx_by_fee = prev_block_cumulative_fee + corrected_issue_amount
            remain_over_issued_icx = remain_over_issued_icx + abs(corrected_issue_amount)
            corrected_issue_amount = 0

        return covered_icx_by_fee, remain_over_issued_icx, corrected_issue_amount

    @staticmethod
    def _separate_icx_and_i_score(i_score: int) -> Tuple[int, int]:
        abs_i_score = abs(i_score)
        over_issued_icx = abs_i_score // I_SCORE_EXCHANGE_RATE
        over_issued_i_score = abs_i_score % I_SCORE_EXCHANGE_RATE
        if i_score < 0:
            over_issued_icx = -over_issued_icx
            over_issued_i_score = -over_issued_i_score

        return over_issued_icx, over_issued_i_score

    def _correct_issue_amount_on_calc_period(self,
                                             prev_calc_period_issued_icx: int,
                                             prev_calc_period_issued_i_score: Optional[int],
                                             remain_over_issued_i_score: int,
                                             icx_issue_amount: int,
                                             prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        assert icx_issue_amount >= 0
        assert prev_block_cumulative_fee >= 0

        # check if RC has sent response about 'CALCULATE' requests. every period should get response
        if prev_calc_period_issued_i_score is None:
            raise AssertionError("There is no prev_calc_period_i_score")

        # get difference between icon_service and reward_calc after set exchange rates
        prev_calc_over_issued_i_score: int = \
            prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score
        total_over_issued_i_score: int = prev_calc_over_issued_i_score + remain_over_issued_i_score
        over_issued_icx, over_issued_i_score = self._separate_icx_and_i_score(total_over_issued_i_score)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, icx_issue_amount = \
            self._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx, prev_block_cumulative_fee)

        remain_over_issued_i_score = remain_over_issued_icx * I_SCORE_EXCHANGE_RATE + over_issued_i_score

        # covered_icx can be negative value (in case of reward calculator having been issued more)
        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_i_score, icx_issue_amount

    def _correct_issue_amount(self,
                              remain_over_issued_i_score: int,
                              icx_issue_amount: int,
                              prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        assert icx_issue_amount >= 0
        assert prev_block_cumulative_fee >= 0

        over_issued_icx, over_issued_i_score = self._separate_icx_and_i_score(remain_over_issued_i_score)

        # covered_icx_by_remain is always positive value
        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, icx_issue_amount = \
            self._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx, prev_block_cumulative_fee)
        remain_over_issued_i_score = remain_over_issued_icx * I_SCORE_EXCHANGE_RATE + over_issued_i_score

        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_i_score, icx_issue_amount
