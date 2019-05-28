from typing import Optional

from iconservice.database.db import ContextDatabase
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.icx_issue_storage import IcxIssueStorage


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
    def _get_difference_between_icon_service_and_reward_calc(icx_amount, i_score_amount) -> int:
        diff = icx_amount * 1_000 - i_score_amount
        return diff

    def _accumulate_current_period_issued_icx(self, context: 'IconScoreContext', issue_amount: int) -> int:
        current_calc_period_issued_amount = self._issue_storage.get_current_calc_period_issued_icx(context)
        current_calc_period_issued_amount += issue_amount
        return current_calc_period_issued_amount

    # calculate diff and return actual issue amount
    def correct_issue_amount_on_calc_period(self,
                                            context: 'IconScoreContext',
                                            prev_calc_period_issued_i_score: Optional[int],
                                            icx_issue_amount: int):
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

            corrected_icx_issue_amount -= over_issued_icx
            if corrected_icx_issue_amount >= 0:
                remain_over_issued_icx = 0
                deducted_icx = over_issued_icx
            else:
                remain_over_issued_icx = abs(corrected_icx_issue_amount)
                corrected_icx_issue_amount = 0
                deducted_icx = icx_issue_amount

            self._issue_storage.put_over_issued_i_score(context, over_issued_i_score)
            self._issue_storage.put_over_issued_icx(context, remain_over_issued_icx)

        # todo: consider about this case i_score none != prev_calc
        # elif prev_calc_period_issued_i_score is None and prev_calc_period_issued_amount is not None:
        #   raise Exception

        self._issue_storage.put_prev_calc_period_issued_icx(context, current_calc_period_total_issued_icx)
        self._issue_storage.put_current_calc_period_issued_icx(context, 0)

        # todo: deducted_icx can be negative. consider about this
        return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount

    def correct_issue_amount(self, context: 'IconScoreContext', icx_issue_amount: int):
        current_calc_period_issued_amount = self._accumulate_current_period_issued_icx(context, icx_issue_amount)
        deducted_icx = 0
        remain_over_issued_icx = self._issue_storage.get_over_issued_icx(context)
        corrected_icx_issue_amount = icx_issue_amount

        if remain_over_issued_icx > 0:
            # todo: same logic..
            corrected_icx_issue_amount -= remain_over_issued_icx
            if corrected_icx_issue_amount >= 0:
                remain_over_issued_icx = 0
                deducted_icx = remain_over_issued_icx
            else:
                remain_over_issued_icx = abs(corrected_icx_issue_amount)
                corrected_icx_issue_amount = 0
                deducted_icx = icx_issue_amount

            self._issue_storage.put_over_issued_icx(context, remain_over_issued_icx)
        # todo: same logic
        self._issue_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_amount)

        return deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount
