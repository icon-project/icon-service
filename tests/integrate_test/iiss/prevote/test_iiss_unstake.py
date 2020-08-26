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
from unittest.mock import patch

from iconservice import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import Revision, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSStake(TestIISSBase):
    def test_unstake(self):
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
        stake: int = 4 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(
            from_=self._accounts[0],
            value=stake
        )
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)

        self.set_revision(Revision.FIX_BALANCE_BUG.value)

        for i in range(1, 5):
            self.set_stake(
                from_=self._accounts[0],
                value=stake - i
            )

        actual_res: dict = self.get_stake(self._accounts[0])
        first_remaining_blocks: int = 16
        expected_res = {
            "stake": stake - 1 * 4,
            "unstakes": [
                {"unstake": 1, "unstakeBlockHeight": 25, "remainingBlocks": first_remaining_blocks},
                {"unstake": 1, "unstakeBlockHeight": 26, "remainingBlocks": first_remaining_blocks+1},
                {"unstake": 1, "unstakeBlockHeight": 27, "remainingBlocks": first_remaining_blocks+2},
                {"unstake": 1, "unstakeBlockHeight": 28, "remainingBlocks": first_remaining_blocks+3},
            ]
        }
        self.assertEqual(expected_res, actual_res)

        # 1st expired unstake
        self.make_empty_blocks(first_remaining_blocks)
        last_balance: int = self.get_balance(self._accounts[0])
        tx_results = self.transfer_icx(from_=self._accounts[0], to_=self._accounts[0], value=0)
        fee = tx_results[0].step_used * tx_results[0].step_price

        actual_res: dict = self.get_stake(self._accounts[0])
        remaining_blocks: int = 0
        expected_res = {
            "stake": stake - 1 * 4,
            "unstakes": [
                {"unstake": 1, "unstakeBlockHeight": 26, "remainingBlocks": remaining_blocks},
                {"unstake": 1, "unstakeBlockHeight": 27, "remainingBlocks": remaining_blocks+1},
                {"unstake": 1, "unstakeBlockHeight": 28, "remainingBlocks": remaining_blocks+2},
            ]
        }
        self.assertEqual(expected_res, actual_res)

        # apply expire balance
        # 2st expired unstake
        self.make_empty_blocks(1)
        
        balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(last_balance - fee + 2, balance)
