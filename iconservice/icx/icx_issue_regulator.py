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

# todo: change to relative path
from iconcommons import Logger

from iconservice.database.db import ContextDatabase
from iconservice.icon_constant import ICON_SERVICE_LOG_TAG
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.icx_issue_storage import IcxIssueStorage


# todo: implement fee related logic
class IcxIssueRegulator:
    _MAX_I_SCORE = 1_000

    def __init__(self):
        self._issue_storage: 'IcxIssueStorage' = None

    def open(self, context_db: 'ContextDatabase'):
        self.close()
        self._issue_storage = IcxIssueStorage(context_db)

    def close(self):
        """Close resources
        """
        if self._issue_storage:
            self._issue_storage.close(context=None)
            self._issue_storage = None

    @staticmethod
    def _reflect_difference_in_issuing(icx_issue_amount: int, over_issued_icx: int) -> Tuple[int, int, int]:
        icx_issue_amount -= over_issued_icx
        if over_issued_icx < 0:
            deducted_icx = -over_issued_icx
            remain_over_issued_icx = 0
            return deducted_icx, remain_over_issued_icx, icx_issue_amount

        if icx_issue_amount >= 0:
            remain_over_issued_icx = 0
            deducted_icx = over_issued_icx
        else:
            remain_over_issued_icx = abs(icx_issue_amount)
            icx_issue_amount = 0
            deducted_icx = icx_issue_amount

        return deducted_icx, remain_over_issued_icx, icx_issue_amount

    def _get_difference_between_icon_service_and_reward_calc(self, icx_amount, i_score_amount) -> int:
        diff = icx_amount * self._MAX_I_SCORE - i_score_amount
        return diff

    def _accumulate_current_period_issued_icx(self, context: 'IconScoreContext', issue_amount: int) -> int:
        current_calc_period_issued_amount = self._issue_storage.get_current_calc_period_issued_icx(context)
        current_calc_period_issued_amount += issue_amount
        return current_calc_period_issued_amount

    # calculate diff and return actual issue amount
    def correct_issue_amount_on_calc_period(self,
                                            context: 'IconScoreContext',
                                            prev_calc_period_issued_i_score: Optional[int],
                                            icx_issue_amount: int) -> Tuple[int, int, int]:
        current_calc_period_total_issued_icx: int = \
            self._accumulate_current_period_issued_icx(context, icx_issue_amount)
        prev_calc_period_issued_icx: Optional[int] = self._issue_storage.get_prev_calc_period_issued_icx(context)
        deducted_icx = 0
        remain_over_issued_icx = self._issue_storage.get_over_issued_icx(context)
        remain_over_issued_i_score = self._issue_storage.get_over_issued_i_score(context)
        corrected_icx_issue_amount = icx_issue_amount

        if prev_calc_period_issued_i_score is not None and prev_calc_period_issued_icx is not None:
            over_issued_i_score: int = \
                self._get_difference_between_icon_service_and_reward_calc(prev_calc_period_issued_icx,
                                                                          prev_calc_period_issued_i_score)
            total_over_issued_i_score: int = over_issued_i_score + \
                                             remain_over_issued_icx * self._MAX_I_SCORE + \
                                             remain_over_issued_i_score

            max_i_score = self._MAX_I_SCORE if total_over_issued_i_score >= 0 else -self._MAX_I_SCORE
            over_issued_icx = total_over_issued_i_score // max_i_score
            over_issued_i_score = total_over_issued_i_score % max_i_score

            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                self._reflect_difference_in_issuing(corrected_icx_issue_amount, over_issued_icx)

            self._issue_storage.put_over_issued_i_score(context, over_issued_i_score)
            self._issue_storage.put_over_issued_icx(context, remain_over_issued_icx)

        elif prev_calc_period_issued_i_score is None and prev_calc_period_issued_icx is not None:
            Logger.error("Reward calculator did not send response to calculate", ICON_SERVICE_LOG_TAG)
            raise Exception("Reward calculator did not send response to calculate")

        self._issue_storage.put_prev_calc_period_issued_icx(context, current_calc_period_total_issued_icx)
        self._issue_storage.put_current_calc_period_issued_icx(context, 0)

        # deducted_icx can be negative value (in case of reward calculator having been issued more)
        return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount

    def correct_issue_amount(self, context: 'IconScoreContext', icx_issue_amount: int) -> Tuple[int, int, int]:
        current_calc_period_issued_icx: int = self._accumulate_current_period_issued_icx(context, icx_issue_amount)
        remain_over_issued_icx: int = self._issue_storage.get_over_issued_icx(context)
        deducted_icx: int = 0

        if remain_over_issued_icx > 0:
            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                self._reflect_difference_in_issuing(icx_issue_amount, remain_over_issued_icx)
            self._issue_storage.put_over_issued_icx(context, remain_over_issued_icx)
        else:
            corrected_icx_issue_amount = icx_issue_amount

        self._issue_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount
