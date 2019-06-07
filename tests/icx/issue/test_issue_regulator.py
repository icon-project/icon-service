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
from iconservice.icon_constant import IconScoreContextType, I_SCORE_EXCHANGE_RATE
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.issue.issue_regulator import IssueRegulator


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
        self.context_db = create_context_db()
        self.issue_regulator = IssueRegulator()
        self.issue_regulator.open(self.context_db)
        self.regulator_storage = self.issue_regulator._regulator_storage

        self.invoke_context = IconScoreContext(IconScoreContextType.INVOKE)
        self.direct_context = IconScoreContext(IconScoreContextType.DIRECT)
        self.query_context = IconScoreContext(IconScoreContextType.QUERY)

    def teardown(self):
        self.issue_regulator.close()

    def test_reflect_difference_in_issuing(self):
        # success case: when input negative over_issued_icx, should return below
        #   deducted_icx = over_issued_icx (i.e. additional issue amount)
        #   remain_over_issued_icx = 0
        #   icx_issue_amount = icx_issue_amount - over_issued_icx
        icx_issue_amount = 1_000
        over_issued_icx = -1_000
        actual_deducted_icx, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
            self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

        assert actual_deducted_icx == over_issued_icx
        assert actual_remain_over_issued_icx == 0
        assert actual_corrected_icx_issue_amount == icx_issue_amount - over_issued_icx

        # success case: when over_issued_icx is more than icx_issue_amount, should return below
        #   deducted_icx = icx_issue_amount (as all icx_issue amount is used to deduct over issued icx)
        #   remain_over_issued_icx = abs(corrected_icx_issue_amount)
        #   icx_issue_amount = 0
        icx_issue_amount = 1_000
        over_issued_icx = 10_000
        actual_deducted_icx, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
            self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

        assert actual_deducted_icx == icx_issue_amount
        assert actual_remain_over_issued_icx == abs(icx_issue_amount - over_issued_icx)
        assert actual_corrected_icx_issue_amount == 0

        # success case: when over_issued_icx is more than icx_issue_amount, should return below
        #   deducted_icx = over_issued_icx (as all over issued icx is deducted from the icx_issue_amount)
        #   remain_over_issued_icx = 0 (as all over issued icx is deducted)
        #   icx_issue_amount = icx_issue_amount - over_issued_icx
        icx_issue_amount = 10_000
        over_issued_icx = 1_000
        actual_deducted_icx, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
            self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

        assert actual_deducted_icx == over_issued_icx
        assert actual_remain_over_issued_icx == 0
        assert actual_corrected_icx_issue_amount == icx_issue_amount - over_issued_icx

        # success case: when input 0, should return below
        #   deducted_icx = 0
        #   remain_over_issued_icx = 0
        #   icx_issue_amount = 0
        icx_issue_amount = 0
        over_issued_icx = 0
        actual_deducted_icx, actual_remain_over_issued_icx, actual_corrected_icx_issue_amount = \
            self.issue_regulator._reflect_difference_in_issuing(icx_issue_amount, over_issued_icx)

        assert actual_deducted_icx == 0
        assert actual_remain_over_issued_icx == 0
        assert actual_corrected_icx_issue_amount == 0

        # failure case: when input negative value as a icx_issue_amount, should raise error
        with pytest.raises(AssertionError):
            self.issue_regulator._reflect_difference_in_issuing(-1_000, 1)

    def test_correct_issue_amount_over_issued_icx_is_less_then_icx_issue_amount(self):
        icx_issue_amount = 10_000
        over_issued_i_score = 1_000 * I_SCORE_EXCHANGE_RATE
        current_calc_period_issued_icx = 50_000
        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount(context, icx_issue_amount)

        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(context) == 0

        assert deducted_icx == over_issued_i_score // I_SCORE_EXCHANGE_RATE
        assert corrected_icx_issue_amount == icx_issue_amount - over_issued_i_score // I_SCORE_EXCHANGE_RATE

    def test_correct_issue_amount_over_issued_icx_is_more_then_icx_issue_amount(self):
        icx_issue_amount = 1_000
        over_issued_i_score = 10_000 * I_SCORE_EXCHANGE_RATE
        over_issued_icx = over_issued_i_score // I_SCORE_EXCHANGE_RATE
        current_calc_period_issued_icx = 50_000
        context = self.direct_context
        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount(context, icx_issue_amount)

        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_icx == over_issued_icx - icx_issue_amount
        assert self.regulator_storage.get_over_issued_i_score(context) == remain_over_issued_icx * I_SCORE_EXCHANGE_RATE

        assert deducted_icx == icx_issue_amount
        assert corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_more_than_0_and_icx_issue_amount_is_0(self):
        icx_issue_amount = 0
        over_issued_i_score = 1_000 * I_SCORE_EXCHANGE_RATE
        over_issued_icx = over_issued_i_score // I_SCORE_EXCHANGE_RATE
        current_calc_period_issued_icx = 50_000
        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount(context, icx_issue_amount)

        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx

        assert remain_over_issued_icx == over_issued_icx
        assert self.regulator_storage.get_over_issued_i_score(context) == over_issued_icx * I_SCORE_EXCHANGE_RATE

        assert deducted_icx == 0
        assert corrected_icx_issue_amount == 0

    def test_correct_issue_amount_over_issued_icx_is_0(self):
        icx_issue_amount = 1_000
        over_issued_i_score = 0
        current_calc_period_issued_icx = 50_000
        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount(context, icx_issue_amount)

        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(context) == 0

        assert deducted_icx == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    def test_correct_issue_amount_less_than_0(self):
        icx_issue_amount = -1000
        over_issued_i_score = 0
        current_calc_period_issued_icx = 50_000
        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        with pytest.raises(AssertionError):
            self.issue_regulator.correct_issue_amount(context, icx_issue_amount)

    def test_correct_issue_amount_on_calc_period_when_first_calc_period(self):
        # success case: when prev issued i score and prev issued icx data is None, should return below
        #   prev calc period icx = current calc period icx, current calc period icx = 0
        #   deducted_icx = 0
        #   remain_over_issued_icx = 0
        #   corrected_icx_issue_amount = icx_issue_amount

        icx_issue_amount = 1000
        over_issued_i_score = 0
        current_calc_period_issued_icx = 50_000
        prev_calc_period_issued_i_score = None

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(context) == 0

        assert deducted_icx == 0
        assert corrected_icx_issue_amount == icx_issue_amount

    def test_correct_issue_amount_on_calc_period_invalid_scenario(self):
        # failure case: when prev issued i score is None but prev issued icx data is exist, should raise error
        icx_issue_amount = 1000
        over_issued_i_score = 0
        current_calc_period_issued_icx = 5_000
        prev_calc_period_issued_i_score = None
        prev_calc_period_issued_icx = 1_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        with pytest.raises(Exception):
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

    def test_correct_issue_amount_on_calc_period_prev_icx_is_more_than_prev_i_score(self):
        # success case: when remain over issued icx + prev calc over issued icx < icx_issue amount
        prev_calc_period_issued_icx = 10_000
        prev_calc_period_issued_i_score = 9_000_325

        icx_issue_amount = 2_000
        over_issued_i_score = 500_400
        current_calc_period_issued_icx = 5_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        remain_i_score = self.regulator_storage.get_over_issued_i_score(self.query_context)

        expected_diff = prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score \
                        + over_issued_i_score
        expected_deducted_icx = (expected_diff // I_SCORE_EXCHANGE_RATE)
        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert deducted_icx == expected_deducted_icx
        assert corrected_icx_issue_amount == icx_issue_amount - deducted_icx

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(
            self.query_context) // I_SCORE_EXCHANGE_RATE == remain_over_issued_icx

        assert remain_i_score == expected_diff - deducted_icx * I_SCORE_EXCHANGE_RATE
        assert remain_i_score % I_SCORE_EXCHANGE_RATE == expected_diff % I_SCORE_EXCHANGE_RATE

        # success case: when remain over issued icx + prev calc over issued icx > icx_issue amount
        icx_issue_amount = 1_000
        over_issued_i_score = 5_000_300
        current_calc_period_issued_icx = 5_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        remain_i_score = self.regulator_storage.get_over_issued_i_score(self.query_context)

        expected_diff = prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score \
                        + over_issued_i_score
        expected_deducted_icx = (expected_diff // I_SCORE_EXCHANGE_RATE)
        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert deducted_icx == icx_issue_amount
        assert corrected_icx_issue_amount == 0

        assert remain_over_issued_icx == expected_deducted_icx - icx_issue_amount
        assert self.regulator_storage.get_over_issued_i_score(self.query_context) // I_SCORE_EXCHANGE_RATE \
               == remain_over_issued_icx

        assert remain_i_score % I_SCORE_EXCHANGE_RATE == expected_diff % I_SCORE_EXCHANGE_RATE

    def test_correct_issue_amount_on_calc_period_prev_icx_is_less_than_prev_i_score(self):
        # success case: when remain over issued icx overwhelm additional issuing amount.
        prev_calc_period_issued_icx = 9_000
        prev_calc_period_issued_i_score = 10_000_325

        icx_issue_amount = 2_000
        over_issued_i_score = 5_000_321
        current_calc_period_issued_icx = 5_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        remain_i_score = self.regulator_storage.get_over_issued_i_score(self.query_context)

        expected_diff = prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score \
                        + over_issued_i_score
        expected_deducted_icx = (expected_diff // I_SCORE_EXCHANGE_RATE)
        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert deducted_icx == icx_issue_amount
        assert corrected_icx_issue_amount == 0

        assert remain_over_issued_icx == expected_deducted_icx - icx_issue_amount
        assert self.regulator_storage.get_over_issued_i_score(self.query_context) // I_SCORE_EXCHANGE_RATE \
               == remain_over_issued_icx

        assert remain_i_score % I_SCORE_EXCHANGE_RATE == expected_diff % I_SCORE_EXCHANGE_RATE

    def test_correct_issue_amount_on_calc_period_prev_icx_is_less_than_prev_i_score_additional_issuing(self):
        # success case: when need additional issuing
        prev_calc_period_issued_icx = 9_000
        prev_calc_period_issued_i_score = 10_000_325

        icx_issue_amount = 2_000
        over_issued_i_score = 100_321
        current_calc_period_issued_icx = 5_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        remain_i_score = self.regulator_storage.get_over_issued_i_score(self.query_context)

        expected_diff = prev_calc_period_issued_icx * I_SCORE_EXCHANGE_RATE - prev_calc_period_issued_i_score \
                        + over_issued_i_score
        expected_deducted_icx = -(expected_diff // -I_SCORE_EXCHANGE_RATE)
        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert deducted_icx == expected_deducted_icx
        assert corrected_icx_issue_amount == icx_issue_amount + (-expected_deducted_icx)

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(self.query_context) // -I_SCORE_EXCHANGE_RATE\
               == remain_over_issued_icx

        assert remain_i_score % -I_SCORE_EXCHANGE_RATE == expected_diff % -I_SCORE_EXCHANGE_RATE

    def test_correct_issue_amount_on_calc_period_prev_icx_and_prev_i_score_is_same(self):
        # success case: when need additional issuing
        prev_calc_period_issued_icx = 10_000
        prev_calc_period_issued_i_score = 10_000_000

        icx_issue_amount = 0
        over_issued_i_score = 0
        current_calc_period_issued_icx = 5_000

        context = self.direct_context

        # setting
        self.regulator_storage.put_over_issued_i_score(context, over_issued_i_score)
        self.regulator_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_icx)
        self.regulator_storage.put_prev_calc_period_issued_icx(context, prev_calc_period_issued_icx)

        deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
            self.issue_regulator.correct_issue_amount_on_calc_period(context,
                                                                     prev_calc_period_issued_i_score,
                                                                     icx_issue_amount)

        remain_i_score = self.regulator_storage.get_over_issued_i_score(self.query_context)
        assert self.regulator_storage.get_current_calc_period_issued_icx(context) == 0
        assert self.regulator_storage.get_prev_calc_period_issued_icx(context) == \
               current_calc_period_issued_icx + icx_issue_amount

        assert deducted_icx == 0
        assert corrected_icx_issue_amount == icx_issue_amount

        assert remain_over_issued_icx == 0
        assert self.regulator_storage.get_over_issued_i_score(self.query_context) == remain_over_issued_icx

        assert remain_i_score == 0
        assert self.regulator_storage.get_over_issued_i_score(self.query_context) == remain_i_score
