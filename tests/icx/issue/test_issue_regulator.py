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

import pytest
from unittest.mock import Mock

from iconservice.database.db import ContextDatabase
from iconservice.icon_constant import IconScoreContextType, ISCORE_EXCHANGE_RATE
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.issue.regulator import Regulator
from iconservice.icx.issue.storage import RegulatorVariable


def create_context_db():
    """
    Create memory db for ContextDatabase

    :return: ContextDatabase
    """
    memory_db = {}

    # noinspection PyUnusedLocal
    def put(context, key, value):
        memory_db[key] = value

    # noinspection PyUnusedLocal
    def get(context, key):
        return memory_db.get(key)

    # noinspection PyUnusedLocal
    def delete(context, key):
        del memory_db[key]

    context_db = Mock(spec=ContextDatabase)
    context_db.get = get
    context_db.put = put
    context_db.delete = delete

    return context_db


class TestIssueRegulator:

    def setup(self):
        self.issue_regulator = Regulator()

        self.invoke_context = IconScoreContext(IconScoreContextType.INVOKE)
        self.direct_context = IconScoreContext(IconScoreContextType.DIRECT)
        self.query_context = IconScoreContext(IconScoreContextType.QUERY)

    def test_reflect_difference_in_issuing(self):
        # success case: when input negative over_issued_icx, should return below
        #   covered_by_fee = cumulative_fee
        #   covered_by_remain = over_issued_icx (i.e. additional issue amount)
        #   remain_over_issued_icx = 0 if cumulative_fee over 1000, cumulative_fee - 1000
        #   icx_issue_amount = icx_issue_amount - over_issued_icx - cumulative_fee
        icx_issue_amount = 1_000
        over_issued_icx = -1_000

        max_covered_by_fee = icx_issue_amount - over_issued_icx
        for cumulative_fee in range(0, 2005):
            actual_covered_by_fee, actual_covered_by_remain, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
                self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount,
                                                                    over_issued_icx,
                                                                    cumulative_fee)
            expected_cumulative_fee = 0 if cumulative_fee <= max_covered_by_fee else cumulative_fee - max_covered_by_fee
            assert actual_covered_by_fee == cumulative_fee if cumulative_fee <= max_covered_by_fee else max_covered_by_fee
            assert actual_covered_by_remain == over_issued_icx
            assert actual_remain_over_issued_icx == expected_cumulative_fee
            assert actual_corrected_icx_issue_amount == icx_issue_amount - over_issued_icx - cumulative_fee \
                if cumulative_fee <= max_covered_by_fee else max_covered_by_fee

        # success case: when over_issued_icx is more than icx_issue_amount, should return below
        #   covered_by_fee = 0
        #   covered_by_remain = icx_issue_amount (as all icx_issue amount is used to deduct over issued icx)
        #   remain_over_issued_icx = abs(corrected_icx_issue_amount) + cumulative_fee
        #   icx_issue_amount = 0
        icx_issue_amount = 1_000
        over_issued_icx = 10_000

        for cumulative_fee in range(0, 2000):
            actual_covered_by_fee, actual_covered_by_remain, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
                self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount,
                                                                    over_issued_icx,
                                                                    cumulative_fee)
            assert actual_covered_by_fee == 0
            assert actual_covered_by_remain == icx_issue_amount
            assert actual_remain_over_issued_icx == abs(icx_issue_amount - over_issued_icx) + cumulative_fee
            assert actual_corrected_icx_issue_amount == 0

        # success case: when over_issued_icx is more than icx_issue_amount, should return below
        #   covered_by_fee = cumulative_fee if cumulative fee is under 1_000, if over, 1000
        #   covered_by_remain = over_issued_icx (as all over issued icx is deducted from the icx_issue_amount)
        #   remain_over_issued_icx = 0 (as all over issued icx is deducted)
        #   icx_issue_amount = icx_issue_amount - over_issued_icx
        icx_issue_amount = 2_000
        over_issued_icx = 1_000
        max_covered_by_fee = icx_issue_amount - over_issued_icx
        for cumulative_fee in range(0, 1005):
            actual_covered_by_fee, actual_covered_by_remain, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
                self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount,
                                                                    over_issued_icx,
                                                                    cumulative_fee)
            assert actual_covered_by_fee == cumulative_fee \
                if cumulative_fee <= max_covered_by_fee else max_covered_by_fee
            assert actual_covered_by_remain == over_issued_icx
            assert actual_remain_over_issued_icx == 0 \
                if cumulative_fee <= max_covered_by_fee else cumulative_fee - max_covered_by_fee
            assert actual_corrected_icx_issue_amount == icx_issue_amount - over_issued_icx - cumulative_fee \
                if cumulative_fee <= max_covered_by_fee else max_covered_by_fee

        # success case: when input 0, should return below
        #   covered_by_fee = 0
        #   covered_by_remain = 0
        #   remain_over_issued_icx = cumulative_fee
        #   icx_issue_amount = 0
        icx_issue_amount = 0
        over_issued_icx = 0
        for cumulative_fee in range(0, 1005):
            actual_covered_by_fee, actual_covered_by_remain, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
                self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount,
                                                                    over_issued_icx,
                                                                    cumulative_fee)

            assert actual_covered_by_fee == 0
            assert actual_covered_by_remain == 0
            assert actual_remain_over_issued_icx == cumulative_fee
            assert actual_corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_less_then_icx_issue_amount(self):
        icx_issue_amount = 10_000
        over_issued_i_score = 1_000 * ISCORE_EXCHANGE_RATE
        prev_block_cumulative_fee = 0
        # current_calc_period_issued_icx = 50_000

        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        # updated_regulator_variable: 'RegulatorVariable' = \
        #     self.regulator_storage.get_regulator_variable(self.direct_context)
        # assert updated_regulator_variable.current_calc_period_issued_icx == \
        #        current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_iscore == 0
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == over_issued_i_score // ISCORE_EXCHANGE_RATE
        assert corrected_icx_issue_amount == icx_issue_amount - over_issued_i_score // ISCORE_EXCHANGE_RATE \
               - prev_block_cumulative_fee

    def test_correct_issue_amount_over_issued_icx_is_more_then_icx_issue_amount(self):
        icx_issue_amount = 1_000
        over_issued_i_score = 10_000 * ISCORE_EXCHANGE_RATE
        prev_block_cumulative_fee = 0
        # current_calc_period_issued_icx = 50_000

        # # setting
        # regulator_variable: 'RegulatorVariable' = self.regulator_storage.get_regulator_variable(self.direct_context)
        # regulator_variable.over_issued_iscore = over_issued_i_score
        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        # updated_regulator_variable: 'RegulatorVariable' = \
        #     self.regulator_storage.get_regulator_variable(self.direct_context)
        # assert updated_regulator_variable.current_calc_period_issued_icx == \
        #        current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_iscore == over_issued_i_score - icx_issue_amount * ISCORE_EXCHANGE_RATE + \
               (prev_block_cumulative_fee * ISCORE_EXCHANGE_RATE)
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == icx_issue_amount
        assert corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_more_than_0_and_icx_issue_amount_is_0(self):
        icx_issue_amount = 0
        prev_block_cumulative_fee = 0
        over_issued_i_score = 1_000 * ISCORE_EXCHANGE_RATE
        over_issued_icx = over_issued_i_score // ISCORE_EXCHANGE_RATE
        # current_calc_period_issued_icx = 50_000
        # context = self.direct_context

        # # setting
        # regulator_variable: 'RegulatorVariable' = self.regulator_storage.get_regulator_variable(self.direct_context)
        # regulator_variable.over_issued_iscore = over_issued_i_score
        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        # updated_regulator_variable: 'RegulatorVariable' = \
        #     self.regulator_storage.get_regulator_variable(self.direct_context)
        # assert updated_regulator_variable.current_calc_period_issued_icx == current_calc_period_issued_icx

        assert remain_over_issued_iscore == over_issued_icx * ISCORE_EXCHANGE_RATE + (prev_block_cumulative_fee * ISCORE_EXCHANGE_RATE)
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == 0
        assert corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_0(self):
        icx_issue_amount = 1_000
        prev_block_cumulative_fee = 0
        over_issued_i_score = 0
        # current_calc_period_issued_icx = 50_000
        # context = self.direct_context

        # setting
        # regulator_variable: 'RegulatorVariable' = self.regulator_storage.get_regulator_variable(self.direct_context)
        # regulator_variable.over_issued_iscore = over_issued_i_score
        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        # updated_regulator_variable: 'RegulatorVariable' = \
        #     self.regulator_storage.get_regulator_variable(self.direct_context)
        # assert updated_regulator_variable.current_calc_period_issued_icx == \
        #        current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_iscore == 0
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    def test_correct_issue_amount_less_than_0(self):
        icx_issue_amount = -1000
        prev_block_cumulative_fee = 0
        over_issued_i_score = 0
        # current_calc_period_issued_icx = 50_000
        # context = self.direct_context

        # # setting
        # regulator_variable: 'RegulatorVariable' = self.regulator_storage.get_regulator_variable(self.direct_context)
        # regulator_variable.over_issued_iscore = over_issued_i_score
        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        with pytest.raises(AssertionError):
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

    def test_correct_issue_amount_fee_less_than_0(self):
        icx_issue_amount = 1000
        prev_block_cumulative_fee = -1000
        over_issued_i_score = 0

        with pytest.raises(AssertionError):
            self.issue_regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

    def test_correct_issue_amount_on_calc_period_when_first_calc_period(self):
        # success case: when prev issued i score and prev issued icx data is zero, should return below
        #   covered_by_fee = 0
        #   covered_by_remain = 0
        #   remain_over_issued_icx = 0
        #   corrected_icx_issue_amount = icx_issue_amount

        icx_issue_amount = 1000
        over_issued_i_score = 0
        prev_block_cumulative_fee = 0
        prev_calc_period_issued_icx = 0
        prev_calc_period_issued_iscore = 0
        #current_calc_period_issued_icx = 50_000

        # context = self.direct_context

        # setting
        # regulator_variable: 'RegulatorVariable' = self.regulator_storage.get_regulator_variable(self.direct_context)
        # regulator_variable.over_issued_iscore = over_issued_i_score
        # regulator_variable.current_calc_period_issued_icx = current_calc_period_issued_icx
        # regulator_variable.prev_calc_period_issued_icx = prev_calc_period_issued_icx
        # self.regulator_storage.put_regulator_variable(self.direct_context, regulator_variable)

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        # updated_regulator_variable: 'RegulatorVariable' = \
        #     self.regulator_storage.get_regulator_variable(self.direct_context)
        # assert updated_regulator_variable.current_calc_period_issued_icx == 0
        # assert updated_regulator_variable.prev_calc_period_issued_icx == \
        #        current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_iscore == 0

        assert covered_icx_by_remain == 0
        assert covered_icx_by_fee == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    def test_correct_issue_amount_on_calc_period_invalid_scenario(self):
        # failure case: when prev issued i score is None, should raise error

        prev_calc_period_issued_icx = 1_000
        prev_calc_period_issued_iscore = None

        prev_block_cumulative_fee = 0
        icx_issue_amount = 1000
        over_issued_i_score = 0

        with pytest.raises(AssertionError):
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

    def test_correct_issue_amount_on_calc_period_prev_icx_is_more_than_prev_i_score(self):
        # success case: when remain over issued icx + prev calc over issued icx < icx_issue amount
        # fee is excluded (i.e. set to zero) as tested before
        prev_calc_period_issued_icx = 10_000
        prev_calc_period_issued_iscore = 9_000_325
        over_issued_i_score = 500_400
        icx_issue_amount = 2_000
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        expected_diff_without_fee = prev_calc_period_issued_icx * ISCORE_EXCHANGE_RATE - prev_calc_period_issued_iscore \
                        + over_issued_i_score
        expected_covered_by_remain = (expected_diff_without_fee // ISCORE_EXCHANGE_RATE)

        assert covered_icx_by_fee == prev_block_cumulative_fee
        assert covered_icx_by_remain == expected_covered_by_remain
        assert corrected_icx_issue_amount == icx_issue_amount - expected_covered_by_remain - prev_block_cumulative_fee
        assert remain_over_issued_iscore == expected_diff_without_fee - expected_covered_by_remain * ISCORE_EXCHANGE_RATE

        # success case: when remain over issued icx + prev calc over issued icx > icx_issue amount
        over_issued_i_score = 5_000_300
        icx_issue_amount = 1_000
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        expected_diff_without_fee = prev_calc_period_issued_icx * ISCORE_EXCHANGE_RATE - prev_calc_period_issued_iscore \
                                    + over_issued_i_score

        assert covered_icx_by_fee == prev_block_cumulative_fee
        assert covered_icx_by_remain == icx_issue_amount
        assert corrected_icx_issue_amount == 0
        assert remain_over_issued_iscore == expected_diff_without_fee - covered_icx_by_remain * ISCORE_EXCHANGE_RATE

    def test_correct_issue_amount_on_calc_period_prev_icx_is_less_than_prev_i_score(self):
        # success case: when remain over issued icx overwhelm additional issuing amount.
        prev_calc_period_issued_icx = 9_000
        prev_calc_period_issued_iscore = 10_000_325

        icx_issue_amount = 2_000
        over_issued_i_score = 5_000_321
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        expected_diff_without_fee = prev_calc_period_issued_icx * ISCORE_EXCHANGE_RATE - prev_calc_period_issued_iscore \
                                    + over_issued_i_score

        assert covered_icx_by_remain == icx_issue_amount
        assert covered_icx_by_fee == prev_block_cumulative_fee
        assert corrected_icx_issue_amount == 0
        assert remain_over_issued_iscore == expected_diff_without_fee - (icx_issue_amount * ISCORE_EXCHANGE_RATE)

    def test_correct_issue_amount_on_calc_period_prev_icx_is_less_than_prev_i_score_additional_issuing(self):
        # success case: when need additional issuing
        prev_calc_period_issued_icx = 9_000
        prev_calc_period_issued_iscore = 10_000_325

        icx_issue_amount = 2_000
        over_issued_i_score = 100_321
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        expected_diff_without_fee = prev_calc_period_issued_icx * ISCORE_EXCHANGE_RATE - prev_calc_period_issued_iscore \
                                    + over_issued_i_score
        expected_covered_by_remain = -(expected_diff_without_fee // -ISCORE_EXCHANGE_RATE)
        assert covered_icx_by_fee == prev_block_cumulative_fee
        assert covered_icx_by_remain == expected_covered_by_remain
        assert corrected_icx_issue_amount == icx_issue_amount + (-expected_covered_by_remain)
        assert remain_over_issued_iscore == expected_diff_without_fee % -ISCORE_EXCHANGE_RATE

    def test_correct_issue_amount_on_calc_period_prev_icx_and_prev_i_score_is_same(self):
        # success case: when need additional issuing
        prev_calc_period_issued_icx = 10_000
        prev_calc_period_issued_iscore = 10_000_000

        icx_issue_amount = 0
        over_issued_i_score = 0
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            self.issue_regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                                      prev_calc_period_issued_iscore,
                                                                      over_issued_i_score,
                                                                      icx_issue_amount,
                                                                      prev_block_cumulative_fee)

        assert covered_icx_by_remain == 0
        assert covered_icx_by_fee == 0
        assert corrected_icx_issue_amount == icx_issue_amount
        assert remain_over_issued_iscore == 0
