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
from unittest.mock import Mock

from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS, ICX_IN_LOOP
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSClaim(TestIISSBase):
    def test_iiss_claim(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REV_IISS)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # stake 10 icx
        stake: int = 10 * ICX_IN_LOOP
        self.set_stake(from_=self._accounts[0],
                       value=stake)

        # set delegation 1 icx addr0 ~ addr9
        delegation_amount: int = 1 * ICX_IN_LOOP
        total_delegating: int = 0
        delegations: list = []
        start_index: int = 0
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: tuple = \
                (
                    self._accounts[start_index + i],
                    delegation_amount
                )
            delegations.append(delegation_info)
            total_delegating += delegation_amount
        self.set_delegation(from_=self._accounts[0],
                            origin_delegations=delegations)

        # claim mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.claim_iscore = Mock(return_value=(iscore, block_height))

        # get_treasury account balance
        treasury_balance_before_claim: int = self.get_balance(self._fee_treasury)

        # claim iscore
        tx_results: List['TransactionResult'] = self.claim_iscore(self._accounts[0])

        accumulative_fee = tx_results[0].step_price * tx_results[0].step_used
        # query mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))

        # query iscore
        response: dict = self.query_iscore(self._accounts[0])
        expected_response = {
            "blockHeight": block_height,
            "estimatedICX": icx,
            "iscore": iscore
        }
        self.assertEqual(expected_response, response)

        # get_treasury account balance after claim
        treasury_balance_after_claim: int = self.get_balance(self._fee_treasury)
        expected_withdraw_icx_amount_from_treasury: int = icx
        self.assertEqual(expected_withdraw_icx_amount_from_treasury,
                         treasury_balance_before_claim - (treasury_balance_after_claim - accumulative_fee))
