# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

"""IconScoreEngine testcase
"""
from typing import TYPE_CHECKING, List

from iconservice.icon_constant import Revision, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSStake(TestIISSBase):
    def test_unstake_balance_rev_10(self):
        self._test_unstake_balance(
            rev=Revision.FIX_UNSTAKE_BUG.value,
            expected_expired_ustake_cnt=2,
            expected_last_balance=0
        )

    def test_unstake_balance_rev_11(self):
        self._test_unstake_balance(
            rev=Revision.FIX_BALANCE_BUG.value,
            expected_expired_ustake_cnt=3,
            expected_last_balance=1 * ICX_IN_LOOP
        )

    def _test_unstake_balance(
            self,
            rev: int,
            expected_expired_ustake_cnt: int,
            expected_last_balance: int
    ):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 10 icx
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=balance
        )

        # set stake
        target_stake: int = 8
        stake: int = target_stake * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(
            from_=self._accounts[0],
            value=stake
        )
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        for i in range(6):
            self.set_stake(
                from_=self._accounts[0],
                value=stake - (i+1) * ICX_IN_LOOP
            )

        last_balance: int = self.get_balance(self._accounts[0])

        actual_res: dict = self.get_stake(self._accounts[0])
        first_remaining_blocks: int = 14
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 25, "remainingBlocks": first_remaining_blocks},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 26, "remainingBlocks": first_remaining_blocks+1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 27, "remainingBlocks": first_remaining_blocks+2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 28, "remainingBlocks": first_remaining_blocks+3},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": first_remaining_blocks+4},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": first_remaining_blocks+5},
            ]
        }
        self.assertEqual(expected_res, actual_res)

        self.set_revision(rev)

        # 1st expired unstake
        self.make_empty_blocks(first_remaining_blocks)
        # len(unstakes_info) = 6
        tx_results = self.transfer_icx(from_=self._accounts[0], to_=self._accounts[1], value=0)
        # len(unstakes_info) = 5
        estimate_fee = tx_results[0].step_used * tx_results[0].step_price

        # 2nd expired unstake
        self.make_empty_blocks(1)
        # len(unstakes_info) = 4

        current_balance: int = self.get_balance(self._accounts[0])
        expected_balance: int = last_balance + 1 * ICX_IN_LOOP * expected_expired_ustake_cnt - estimate_fee
        self.assertEqual(current_balance, expected_balance)

        self.transfer_icx(
            from_=self._accounts[0],
            to_=self._accounts[1],
            value=expected_balance-estimate_fee,
            disable_pre_validate=True,
            step_limit=1 * 10 ** 5,
            expected_status=True
        )

        # len(unstakes_info) = 3

        balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(balance, expected_last_balance)
