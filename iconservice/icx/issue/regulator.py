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

from typing import Optional, Tuple, TYPE_CHECKING

from iconcommons import Logger

from ...base.exception import FatalException
from ...icon_constant import ISCORE_EXCHANGE_RATE, IISS_LOG_TAG

if TYPE_CHECKING:
    from .storage import RegulatorVariable
    from ...iconscore.icon_score_context import IconScoreContext


class Regulator:
    """ Regulate ICX issue amount
    * The difference of I-SCORE calculation between icon service and reward calculator
    * Fee from the transaction

    covered_icx_by_fee:
    Used for generating coin base transaction and emitting event log

    covered_icx_by_over_issue:
    Used for generating coin base transaction and emitting event log. It could be
    negative value (In case that Reward calculator issued ICX more then Icon service)

    remain_over_issued_icx:
    Only used for emitting eventlog

    corrected_icx_issue_amount:
    Used for issuing, generating coin base transaction and emitting event log
    """
    def __init__(self, context: 'IconScoreContext', issue_amount: int):
        self._regulator_variable: Optional['RegulatorVariable'] = None
        self._covered_icx_by_fee: Optional[int] = None
        self._covered_icx_by_remain: Optional[int] = None
        self._corrected_icx_issue_amount: Optional[int] = None

        self._set_corrected_issue_data(context, issue_amount)

    @property
    def covered_icx_by_fee(self) -> int:
        return self._covered_icx_by_fee

    @property
    def covered_icx_by_over_issue(self) -> int:
        return self._covered_icx_by_remain

    @property
    def remain_over_issued_icx(self) -> int:
        return self._regulator_variable.over_issued_iscore // ISCORE_EXCHANGE_RATE

    @property
    def corrected_icx_issue_amount(self) -> int:
        return self._corrected_icx_issue_amount

    def _set_corrected_issue_data(self, context: 'IconScoreContext', issue_amount: int):
        regulator_variable: 'RegulatorVariable' = context.storage.issue.get_regulator_variable(context)
        prev_block_cumulative_fee: int = context.storage.icx.last_block.cumulative_fee
        end_block_height_of_calc: int = context.storage.iiss.get_end_block_height_of_calc(context)

        # Update current calculated period total issued icx
        current_calc_period_total_issued_icx: int = regulator_variable.current_calc_period_issued_icx
        current_calc_period_total_issued_icx += issue_amount
        if end_block_height_of_calc == context.block.height:
            prev_calc_period_issued_iscore, _, _ = context.storage.rc.get_calc_response_from_rc()

            assert prev_calc_period_issued_iscore >= 0

            # In case of the first term of decentralization.
            # Do not regulate on the first term of decentralization
            # as Icon service has not issued ICX on the last period of 'pre-vote'
            # (On pre-vote, icon-foundation provided ICX instead of issuing it)
            if regulator_variable.prev_calc_period_issued_icx == -1:
                regulator_variable.prev_calc_period_issued_icx, prev_calc_period_issued_iscore = 0, 0
            covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
                self._correct_issue_amount_on_calc_period(regulator_variable.prev_calc_period_issued_icx,
                                                          prev_calc_period_issued_iscore,
                                                          regulator_variable.over_issued_iscore,
                                                          issue_amount,
                                                          prev_block_cumulative_fee)

            regulator_variable.prev_calc_period_issued_icx = current_calc_period_total_issued_icx
            regulator_variable.current_calc_period_issued_icx = 0
        else:
            covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
                self._correct_issue_amount(regulator_variable.over_issued_iscore,
                                           issue_amount,
                                           prev_block_cumulative_fee)
            regulator_variable.current_calc_period_issued_icx = current_calc_period_total_issued_icx
        regulator_variable.over_issued_iscore = remain_over_issued_iscore

        self._regulator_variable = regulator_variable
        self._covered_icx_by_fee = covered_icx_by_fee
        self._covered_icx_by_remain = covered_icx_by_remain
        self._corrected_icx_issue_amount = corrected_icx_issue_amount
        Logger.info(f"Regulate BH: {context.block.height} "
                    f"Covered by fee: {self._covered_icx_by_fee} "
                    f"Covered by remain: {self._covered_icx_by_remain} "
                    f"Corrected issue amount {self._corrected_icx_issue_amount}"
                    f"Regulator variable: {self._regulator_variable}", IISS_LOG_TAG)

    def put_regulate_variable(self, context: 'IconScoreContext'):
        context.storage.issue.put_regulator_variable(context, self._regulator_variable)

    @classmethod
    def _reflect_difference_in_issuing(cls,
                                       icx_issue_amount: int,
                                       over_issued_icx: int,
                                       prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        # cover about over issued icx
        # remain_over_issued_icx, corrected_icx_issue_amount
        covered_icx_by_remain, remain_over_issued_icx, corrected_icx_issue_amount = \
            cls._calculate_over_issued_icx(icx_issue_amount,
                                           over_issued_icx)

        covered_icx_by_fee, remain_over_issued_icx, corrected_icx_issue_amount = \
            cls._calculate_prev_block_cumulative_fee(remain_over_issued_icx,
                                                     corrected_icx_issue_amount,
                                                     prev_block_cumulative_fee)

        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, corrected_icx_issue_amount

    @classmethod
    def _calculate_over_issued_icx(cls,
                                   icx_issue_amount: int,
                                   over_issued_icx: int) -> Tuple[int, int, int]:
        corrected_issue_amount = icx_issue_amount - over_issued_icx
        # In case that Reward calculator issued ICX more then Icon service
        if over_issued_icx < 0:
            remain_over_issued_icx = 0
            covered_icx_by_remain = over_issued_icx
            return covered_icx_by_remain, remain_over_issued_icx, corrected_issue_amount

        if corrected_issue_amount >= 0:
            remain_over_issued_icx = 0
            covered_icx_by_remain = over_issued_icx
        else:
            remain_over_issued_icx = abs(corrected_issue_amount)
            corrected_issue_amount = 0
            covered_icx_by_remain = icx_issue_amount

        return covered_icx_by_remain, remain_over_issued_icx, corrected_issue_amount

    @classmethod
    def _calculate_prev_block_cumulative_fee(cls,
                                             remain_over_issued_icx: int,
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

    @classmethod
    def _calculate_prev_block_cumulative_fee(cls,
                                             remain_over_issued_icx: int,
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

    @classmethod
    def _separate_icx_and_iscore(cls, iscore: int) -> Tuple[int, int]:
        abs_iscore = abs(iscore)
        over_issued_icx = abs_iscore // ISCORE_EXCHANGE_RATE
        over_issued_iscore = abs_iscore % ISCORE_EXCHANGE_RATE
        if iscore < 0:
            over_issued_icx = -over_issued_icx
            over_issued_iscore = -over_issued_iscore

        return over_issued_icx, over_issued_iscore

    @classmethod
    def _correct_issue_amount_on_calc_period(cls,
                                             prev_calc_period_issued_icx: int,
                                             prev_calc_period_issued_iscore: int,
                                             remain_over_issued_iscore: int,
                                             icx_issue_amount: int,
                                             prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        """

        :param prev_calc_period_issued_icx: Calculated from Icon Service
        :param prev_calc_period_issued_iscore: Calculated from Reward Calculator
        :param remain_over_issued_iscore: Amount
        :param icx_issue_amount:
        :param prev_block_cumulative_fee:
        :return:
        """
        assert icx_issue_amount >= 0
        assert prev_block_cumulative_fee >= 0
        assert prev_calc_period_issued_iscore >= 0

        prev_calc_over_issued_iscore: int = \
            prev_calc_period_issued_icx * ISCORE_EXCHANGE_RATE - prev_calc_period_issued_iscore
        total_over_issued_iscore: int = prev_calc_over_issued_iscore + remain_over_issued_iscore
        # Over issued amount could be negative value. It means reward calculator issued more then icon service.
        over_issued_icx, over_issued_iscore = cls._separate_icx_and_iscore(total_over_issued_iscore)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, icx_issue_amount = \
            cls._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx, prev_block_cumulative_fee)

        remain_over_issued_iscore: int = remain_over_issued_icx * ISCORE_EXCHANGE_RATE + over_issued_iscore

        # covered_icx can be negative value (in case of reward calculator having been issued more)
        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, icx_issue_amount

    @classmethod
    def _correct_issue_amount(cls,
                              remain_over_issued_iscore: int,
                              icx_issue_amount: int,
                              prev_block_cumulative_fee: int) -> Tuple[int, int, int, int]:
        assert icx_issue_amount >= 0
        assert prev_block_cumulative_fee >= 0

        over_issued_icx, over_issued_iscore = cls._separate_icx_and_iscore(remain_over_issued_iscore)

        # covered_icx_by_remain is always positive value
        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_icx, icx_issue_amount = \
            cls._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx, prev_block_cumulative_fee)
        remain_over_issued_iscore: int = remain_over_issued_icx * ISCORE_EXCHANGE_RATE + over_issued_iscore

        return covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, icx_issue_amount
