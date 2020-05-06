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

import pytest

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, Revision, ICX_IN_LOOP
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSClaim(TestIISSBase):
    def test_iiss_claim(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1], init_balance=balance)

        # stake 10 icx
        stake: int = 10 * ICX_IN_LOOP
        self.set_stake(from_=self._accounts[0], value=stake)

        # set delegation 1 icx addr0 ~ addr9
        delegation_amount: int = 1 * ICX_IN_LOOP
        total_delegating: int = 0
        delegations: list = []
        start_index: int = 0
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: tuple = (
                self._accounts[start_index + i],
                delegation_amount,
            )
            delegations.append(delegation_info)
            total_delegating += delegation_amount
        self.set_delegation(from_=self._accounts[0], origin_delegations=delegations)

        # claim mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.claim_iscore = Mock(return_value=(iscore, block_height))
        RewardCalcProxy.commit_claim = Mock()

        # get_treasury account balance
        treasury_balance_before_claim: int = self.get_balance(self._fee_treasury)

        # claim iscore
        tx_results: List["TransactionResult"] = self.claim_iscore(self._accounts[0])
        self.assertEqual(1, len(tx_results[0].event_logs))
        self.assertEqual(
            SYSTEM_SCORE_ADDRESS, tx_results[0].event_logs[0].score_address
        )
        self.assertEqual(
            ["IScoreClaimed(int,int)"], tx_results[0].event_logs[0].indexed
        )
        self.assertEqual([iscore, icx], tx_results[0].event_logs[0].data)
        RewardCalcProxy.commit_claim.assert_called()

        accumulative_fee = tx_results[0].step_price * tx_results[0].step_used
        # query mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))

        # query iscore with an invalid address
        self._query_iscore_with_invalid_params()

        # query iscore with a valid address
        response: dict = self.query_iscore(self._accounts[0])
        expected_response = {
            "blockHeight": block_height,
            "estimatedICX": icx,
            "iscore": iscore,
        }
        self.assertEqual(expected_response, response)

        # get_treasury account balance after claim
        treasury_balance_after_claim: int = self.get_balance(self._fee_treasury)
        expected_withdraw_icx_amount_from_treasury: int = icx
        self.assertEqual(
            expected_withdraw_icx_amount_from_treasury,
            treasury_balance_before_claim
            - (treasury_balance_after_claim - accumulative_fee),
        )

        # 0 claim mocking
        block_height = 10 ** 2 + 1
        icx = 0
        iscore = icx * 10 ** 3
        RewardCalcProxy.claim_iscore = Mock(return_value=(iscore, block_height))
        RewardCalcProxy.commit_claim = Mock()

        # claim iscore
        tx_results: List["TransactionResult"] = self.claim_iscore(self._accounts[0])
        self.assertEqual(1, len(tx_results[0].event_logs))
        self.assertEqual(
            SYSTEM_SCORE_ADDRESS, tx_results[0].event_logs[0].score_address
        )
        self.assertEqual(
            ["IScoreClaimed(int,int)"], tx_results[0].event_logs[0].indexed
        )
        self.assertEqual([icx, iscore], tx_results[0].event_logs[0].data)
        RewardCalcProxy.commit_claim.assert_not_called()

        # TEST: claim iscore with value should fail
        expected_status = False
        tx = self.create_score_call_tx(
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
            func_name="claimIScore",
            params={},
            value=5,
        )

        self.process_confirm_block_tx([tx], expected_status=expected_status)

    def _query_iscore_with_invalid_params(self):
        params = {
            "version": self._version,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {"method": "queryIScore"},
        }

        # query iscore without an address
        with pytest.raises(TypeError):
            self.icon_service_engine.query("icx_call", params)

        # query iscore with an empty string as an address
        params["data"]["params"] = {"address": ""}
        with pytest.raises(InvalidParamsException):
            self.icon_service_engine.query("icx_call", params)

        # query iscore with an invalid address
        params["data"]["params"] = {"address": "hx1234"}
        with pytest.raises(InvalidParamsException):
            self.icon_service_engine.query("icx_call", params)
