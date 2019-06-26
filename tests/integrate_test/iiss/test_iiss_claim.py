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

from typing import TYPE_CHECKING
from unittest.mock import Mock

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegrateIISSClaim(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision: int):
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'setRevision',
                                      {"code": hex(revision),
                                       "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS,
                                      'setStake',
                                      {"value": hex(value)})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list):
        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'setDelegation',
                                      {"delegations": delegations})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _claim(self, address: 'Address'):
        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'claimIScore',
                                      {})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_iiss_claim(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        # gain 10 icx
        balance: int = 10 * 10 ** 18
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # stake 10 icx
        stake: int = balance
        self._stake(self._addr_array[0], stake)

        # delegation 1 icx
        delegations: list = []
        delegation_amount: int = 1 * 10 ** 18
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: dict = {
                "address": str(self._addr_array[i]),
                "value": hex(delegation_amount)
            }
            delegations.append(delegation_info)

        self._delegate(self._addr_array[0], delegations)

        # claim
        self._claim(self._addr_array[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "queryIScore",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        block_height = 1000000000000000000
        icx = 1000000000000000000
        iscore = icx * 10**3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))
        response = self._query(query_request)
        expected_response = {
            "blockHeight": block_height,
            "icx": icx,
            "iscore": iscore
        }
        self.assertEqual(expected_response, response)
