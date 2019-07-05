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

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegrateIISSDelegation(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision: int):
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'setRevision',
                                      {"code": hex(revision),
                                       "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS,
                                      'setStake',
                                      {"value": hex(value)})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list) -> List['TransactionResult']:
        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'setDelegation',
                                      {"delegations": delegations})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        return tx_results

    def _get_delegation(self, address: 'Address') -> dict:
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getDelegation",
                "params": {
                    "address": str(address)
                }
            }
        }
        return self._query(query_request)

    def test_iiss_delegations_with_duplicated_addresses(self):
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

        # delegate 1 icx to the same addr1 10 times in one request
        delegations: list = []
        delegation_amount: int = 1 * 10 ** 18
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: dict = {
                "address": str(self._addr_array[1]),
                "value": hex(delegation_amount)
            }
            delegations.append(delegation_info)

        # setDelegation request will be failed due to duplicated addresses
        tx_results = self._delegate(self._addr_array[0], delegations)
        tx_result: 'TransactionResult' = tx_results[0]

        assert len(tx_results) == 1
        assert isinstance(tx_results, list)
        assert isinstance(tx_result, TransactionResult)
        assert tx_result.status == 0  # Failure
        assert tx_result.failure.code == ExceptionCode.INVALID_PARAMETER

        response: dict = self._get_delegation(self._addr_array[0])
        delegations: list = response['delegations']
        total_delegated: int = response['totalDelegated']
        self.assertEqual(0, len(delegations))
        self.assertEqual(0, total_delegated)

    def test_iiss_delegation(self):
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

        # delegation 1 icx addr0 ~ addr9
        delegations: list = []
        delegation_amount: int = 1 * 10 ** 18
        total_delegating: int = 0

        # for i in range(IISS_MAX_DELEGATIONS):
        for i in range(1):
            delegation_info: dict = {
                "address": str(self._addr_array[i]),
                "value": hex(delegation_amount)
            }
            delegations.append(delegation_info)
            total_delegating += delegation_amount

        self._delegate(self._addr_array[0], delegations)

        response: dict = self._get_delegation(self._addr_array[0])
        actual_response = []
        for info in response["delegations"]:
            ret_info: dict = {
                "address": str(info["address"]),
                "value": hex(info["value"])
            }
            actual_response.append(ret_info)

        expected_response = delegations
        self.assertEqual(expected_response, actual_response)
        self.assertEqual(total_delegating, response["totalDelegated"])

        # other delegation 1 icx addr10 ~ addr19
        delegations: list = []
        delegation_amount: int = 1 * 10 ** 18
        total_delegating = 0

        for i in range(1):
            delegation_info: dict = {
                "address": str(self._addr_array[i + 10]),
                "value": hex(delegation_amount)
            }
            print(delegation_info)
            delegations.append(delegation_info)
            total_delegating += delegation_amount

        self._delegate(self._addr_array[0], delegations)

        response: dict = self._get_delegation(self._addr_array[0])
        actual_response = []
        for info in response["delegations"]:
            ret_info: dict = {
                "address": str(info["address"]),
                "value": hex(info["value"])
            }
            actual_response.append(ret_info)

        expected_response = delegations
        self.assertEqual(expected_response, actual_response)
        self.assertEqual(total_delegating, response["totalDelegated"])
