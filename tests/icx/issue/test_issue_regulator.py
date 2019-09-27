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

from unittest.mock import Mock, patch

import pytest

from iconservice.base.block import Block
from iconservice.base.exception import FatalException
from iconservice.icon_constant import IconScoreContextType, ISCORE_EXCHANGE_RATE
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.issue.regulator import Regulator
from iconservice.icx.issue.storage import RegulatorVariable
from tests import create_block_hash
from tests.integrate_test import create_timestamp


class TestIssueRegulator:

    def setup(self):
        self.context = IconScoreContext(IconScoreContextType.INVOKE)

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
                Regulator._reflect_difference_in_issuing(icx_issue_amount,
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
                Regulator._reflect_difference_in_issuing(icx_issue_amount,
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
                Regulator._reflect_difference_in_issuing(icx_issue_amount,
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
                Regulator._reflect_difference_in_issuing(icx_issue_amount,
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

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        assert remain_over_issued_iscore == 0
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == over_issued_i_score // ISCORE_EXCHANGE_RATE
        assert corrected_icx_issue_amount == icx_issue_amount - over_issued_i_score // ISCORE_EXCHANGE_RATE \
               - prev_block_cumulative_fee

    def test_correct_issue_amount_over_issued_icx_is_more_then_icx_issue_amount(self):
        icx_issue_amount = 1_000
        over_issued_i_score = 10_000 * ISCORE_EXCHANGE_RATE
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

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

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        assert remain_over_issued_iscore == over_issued_icx * ISCORE_EXCHANGE_RATE + (prev_block_cumulative_fee * ISCORE_EXCHANGE_RATE)
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == 0
        assert corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_0(self):
        icx_issue_amount = 1_000
        prev_block_cumulative_fee = 0
        over_issued_i_score = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

        assert remain_over_issued_iscore == 0
        assert covered_icx_by_fee == 0
        assert covered_icx_by_remain == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    def test_correct_issue_amount_less_than_0(self):
        icx_issue_amount = -1000
        prev_block_cumulative_fee = 0
        over_issued_i_score = 0

        with pytest.raises(AssertionError):
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

    def test_correct_issue_amount_fee_less_than_0(self):
        icx_issue_amount = 1000
        prev_block_cumulative_fee = -1000
        over_issued_i_score = 0

        with pytest.raises(AssertionError):
            Regulator._correct_issue_amount(over_issued_i_score, icx_issue_amount, prev_block_cumulative_fee)

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

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                           prev_calc_period_issued_iscore,
                                                           over_issued_i_score,
                                                           icx_issue_amount,
                                                           prev_block_cumulative_fee)

        assert remain_over_issued_iscore == 0

        assert covered_icx_by_remain == 0
        assert covered_icx_by_fee == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    # Before, there were case that prev_calc_period_issued_iscore is -1, but now, removed this case
    # def test_correct_issue_amount_on_calc_period_invalid_scenario(self):
    #     # failure case: when prev issued i score is None, should raise error
    #
    #     prev_calc_period_issued_icx = 1_000
    #     prev_calc_period_issued_iscore = -1
    #
    #     prev_block_cumulative_fee = 0
    #     icx_issue_amount = 1000
    #     over_issued_i_score = 0
    #
    #     with pytest.raises(FatalException):
    #         Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
    #                                                        prev_calc_period_issued_iscore,
    #                                                        over_issued_i_score,
    #                                                        icx_issue_amount,
    #                                                        prev_block_cumulative_fee)

    def test_correct_issue_amount_on_calc_period_prev_icx_is_more_than_prev_i_score(self):
        # success case: when remain over issued icx + prev calc over issued icx < icx_issue amount
        # fee is excluded (i.e. set to zero) as tested before
        prev_calc_period_issued_icx = 10_000
        prev_calc_period_issued_iscore = 9_000_325
        over_issued_i_score = 500_400
        icx_issue_amount = 2_000
        prev_block_cumulative_fee = 0

        covered_icx_by_fee, covered_icx_by_remain, remain_over_issued_iscore, corrected_icx_issue_amount = \
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
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
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
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
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
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
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
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
            Regulator._correct_issue_amount_on_calc_period(prev_calc_period_issued_icx,
                                                           prev_calc_period_issued_iscore,
                                                           over_issued_i_score,
                                                           icx_issue_amount,
                                                           prev_block_cumulative_fee)

        assert covered_icx_by_remain == 0
        assert covered_icx_by_fee == 0
        assert corrected_icx_issue_amount == icx_issue_amount
        assert remain_over_issued_iscore == 0

    def _create_dummy_block_by_height(self, height: int):
        block_hash = create_block_hash()
        prev_block_hash = create_block_hash()
        timestamp_us = create_timestamp()
        return Block(height, block_hash, timestamp_us, prev_block_hash, 0)

    @patch('iconservice.iconscore.icon_score_context.IconScoreContext.storage')
    def test_set_corrected_issue_data_with_in_period(self,
                                                     mocked_context_storage):
        # create dummy block
        block_height = 5
        block = self._create_dummy_block_by_height(block_height)
        self.context.block = block

        # set regulator_variable
        over_issued_i_score = 0
        current_calc_preiod_issued_icx = 50_000
        prev_calc_period_issued_icx = 5_000
        rv = RegulatorVariable(current_calc_preiod_issued_icx,
                               prev_calc_period_issued_icx,
                               over_issued_i_score)
        cumulative_fee = 0
        issue_amount = 10_000
        mocked_context_storage.icx.last_block.cumulative_fee = cumulative_fee
        mocked_context_storage.iiss.get_end_block_height_of_calc = Mock(return_value=block_height - 1)
        mocked_context_storage.issue.get_regulator_variable = Mock(return_value=rv)
        regulator = Regulator(self.context, issue_amount)

        actual_current_icx = regulator._regulator_variable.current_calc_period_issued_icx
        actual_prev_icx = regulator._regulator_variable.prev_calc_period_issued_icx
        assert actual_current_icx == issue_amount + current_calc_preiod_issued_icx
        assert actual_prev_icx == prev_calc_period_issued_icx

    @patch('iconservice.iconscore.icon_score_context.IconScoreContext.engine')
    @patch('iconservice.iconscore.icon_score_context.IconScoreContext.storage')
    def test_set_corrected_issue_data_end_of_period(self,
                                                    mocked_context_storage,
                                                    mocked_context_engine):
        # create dummy block
        block_height = 5
        block = self._create_dummy_block_by_height(block_height)
        self.context.block = block

        # set regulator_variable
        over_issued_i_score = 0
        current_calc_preiod_issued_icx = 50_000
        prev_calc_period_issued_icx = 5_000
        rv = RegulatorVariable(current_calc_preiod_issued_icx,
                               prev_calc_period_issued_icx,
                               over_issued_i_score)
        cumulative_fee = 0
        issue_amount = 10_000
        mocked_context_storage.icx.last_block.cumulative_fee = cumulative_fee
        mocked_context_engine.prep.term.sequence = 0
        mocked_context_storage.rc.get_calc_response_from_rc = Mock(return_value=(0, 0, None))
        mocked_context_storage.iiss.get_end_block_height_of_calc = Mock(return_value=block_height)
        mocked_context_storage.issue.get_regulator_variable = Mock(return_value=rv)
        regulator = Regulator(self.context, issue_amount)

        actual_current_icx = regulator._regulator_variable.current_calc_period_issued_icx
        actual_prev_icx = regulator._regulator_variable.prev_calc_period_issued_icx
        assert actual_current_icx == 0
        assert actual_prev_icx == issue_amount + current_calc_preiod_issued_icx

    @patch('iconservice.iconscore.icon_score_context.IconScoreContext.engine')
    @patch('iconservice.iconscore.icon_score_context.IconScoreContext.storage')
    def test_set_negative_value_to_prev_calc_preiod_issued_icx(self,
                                                               mocked_context_storage,
                                                               mocked_context_engine):
        # success case: if 'prev_calc_preiod_issued_icx' is -1, should not regulate ICX even though
        # prev_calc_preiod_issued_iscore is exists

        # create dummy block
        block_height = 5
        block = self._create_dummy_block_by_height(block_height)
        self.context.block = block

        # set regulator_variable
        over_issued_i_score = 0
        current_calc_preiod_issued_icx = 50_000_000
        prev_calc_period_issued_icx = -1
        prev_calc_period_issued_iscore = 50_000_000_000_000
        rv = RegulatorVariable(current_calc_preiod_issued_icx,
                               prev_calc_period_issued_icx,
                               over_issued_i_score)
        cumulative_fee = 0
        issue_amount = 10_000_000

        mocked_context_storage.icx.last_block.cumulative_fee = cumulative_fee
        mocked_context_engine.prep.term.sequence = 0
        mocked_context_storage.rc.get_calc_response_from_rc = Mock(return_value=(prev_calc_period_issued_iscore, 0, None))
        mocked_context_storage.iiss.get_end_block_height_of_calc = Mock(return_value=block_height)
        mocked_context_storage.issue.get_regulator_variable = Mock(return_value=rv)
        regulator = Regulator(self.context, issue_amount)

        assert regulator._regulator_variable.prev_calc_period_issued_icx == issue_amount + current_calc_preiod_issued_icx
        assert regulator._regulator_variable.current_calc_period_issued_icx == 0
        assert regulator._regulator_variable.over_issued_iscore == 0
        assert regulator.corrected_icx_issue_amount == issue_amount
        assert regulator.covered_icx_by_over_issue == 0
