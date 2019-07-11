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

from unittest.mock import Mock

from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS, ICX_IN_LOOP
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSClaim(TestIISSBase):

    def test_iiss_claim(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # stake 10 icx
        stake: int = 10 * ICX_IN_LOOP
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set delegation 1 icx addr0 ~ addr9
        delegation_amount: int = 1 * ICX_IN_LOOP
        total_delegating: int = 0
        delegations: list = []
        start_index: int = 0
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: tuple = \
                (
                    self._addr_array[start_index + i],
                    delegation_amount
                )
            delegations.append(delegation_info)
            total_delegating += delegation_amount
        tx: dict = self.create_set_delegation_tx(self._addr_array[0], delegations)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # claim mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.claim_iscore = Mock(return_value=(iscore, block_height))

        # claim iscore
        tx: dict = self.create_claim_tx(self._addr_array[0])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # query mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))

        # query iscore
        response: dict = self.query_iscore(self._addr_array[0])
        expected_response = {
            "blockHeight": block_height,
            "icx": icx,
            "iscore": iscore
        }
        self.assertEqual(expected_response, response)
