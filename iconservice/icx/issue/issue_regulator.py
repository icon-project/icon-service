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

from .regulator_storage import RegulatorStorage
from ...database.db import ContextDatabase
from ...icon_constant import I_SCORE_EXCHANGE_RATE
from ...iconscore.icon_score_context import IconScoreContext


# todo: implement fee related logic
class IssueRegulator:

    def __init__(self):
        self._regulator_storage: 'RegulatorStorage' = None

    def open(self, context_db: 'ContextDatabase'):
        self.close()
        self._regulator_storage = RegulatorStorage(context_db)

    def close(self):
        """Close resources
        """
        if self._regulator_storage:
            self._regulator_storage.close(context=None)
            self._regulator_storage = None

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

    def correct_issue_amount_on_calc_period(self,
                                            context: 'IconScoreContext',
                                            prev_calc_period_issued_i_score: Optional[int],
                                            icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        current_calc_period_total_issued_icx: int = self._regulator_storage.get_current_calc_period_issued_icx(context)
        prev_calc_period_issued_icx: Optional[int] = self._regulator_storage.get_prev_calc_period_issued_icx(context)
        remain_over_issued_icx: int = self._regulator_storage.get_over_issued_icx(context)
        remain_over_issued_i_score: int = self._regulator_storage.get_over_issued_i_score(context)
        deducted_icx = 0

        current_calc_period_total_issued_icx += icx_issue_amount

        if prev_calc_period_issued_i_score is not None and prev_calc_period_issued_icx is not None:
            # get difference between icon_service and reward_calc after set exchange rates
            over_issued_i_score: int = \
                prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score

            total_over_issued_i_score: int = over_issued_i_score + \
                                             remain_over_issued_icx * I_SCORE_EXCHANGE_RATE + \
                                             remain_over_issued_i_score

            over_issued_icx, over_issued_i_score = self._separate_icx_and_i_score(total_over_issued_i_score)

            deducted_icx, remain_over_issued_icx, icx_issue_amount = \
                self._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

            self._regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
            self._regulator_storage.put_over_issued_icx(context, remain_over_issued_icx)

        # dose not consider about opposite case (i score is not None but prev_calc_period_issued_icx is None)
        elif prev_calc_period_issued_i_score is None and prev_calc_period_issued_icx is not None:
            raise Exception("There is no prev_calc_period_i_score data even though calc period")

        self._regulator_storage.put_prev_calc_period_issued_icx(context, current_calc_period_total_issued_icx)
        self._regulator_storage.put_current_calc_period_issued_icx(context, 0)

        # deducted_icx can be negative value (in case of reward calculator having been issued more)
        return deducted_icx, remain_over_issued_icx, icx_issue_amount

    def correct_issue_amount(self, context: 'IconScoreContext', icx_issue_amount: int) -> Tuple[int, int, int]:
        assert icx_issue_amount >= 0

        current_calc_period_total_issued_icx: int = self._regulator_storage.get_current_calc_period_issued_icx(context)
        remain_over_issued_icx: int = self._regulator_storage.get_over_issued_icx(context)
        deducted_icx: int = 0

        current_calc_period_total_issued_icx += icx_issue_amount

        if remain_over_issued_icx > 0:
            deducted_icx, remain_over_issued_icx, icx_issue_amount = \
                self._reflect_difference_in_issuing(icx_issue_amount, remain_over_issued_icx)
            self._regulator_storage.put_over_issued_icx(context, remain_over_issued_icx)
        self._regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_total_issued_icx)

        return deducted_icx, remain_over_issued_icx, icx_issue_amount
