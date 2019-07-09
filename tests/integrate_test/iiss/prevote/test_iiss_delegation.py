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

from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS, ICX_IN_LOOP
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSDelegate(TestIISSBase):

    def test_delegations_with_duplicated_addresses(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # gain 10 icx
        balance: int = 10 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # stake 10 icx
        stake: int = balance
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # delegate 1 icx to the same addr1 10 times in one request
        delegations: list = []
        delegation_amount: int = 1 * ICX_IN_LOOP
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: tuple = \
                (
                    self._addr_array[1],
                    delegation_amount
                )
            delegations.append(delegation_info)

        # setDelegation request will be failed due to duplicated addresses
        tx: dict = self.create_set_delegation_tx(self._addr_array[0], delegations)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(False), tx_results[0].status)
        self._write_precommit_state(prev_block)
        tx_result: 'TransactionResult' = tx_results[0]
        assert len(tx_results) == 1
        assert isinstance(tx_results, list)
        assert isinstance(tx_result, TransactionResult)
        assert tx_result.status == 0  # Failure
        assert tx_result.failure.code == ExceptionCode.INVALID_PARAMETER

        # get delegation
        response: dict = self.get_delegation(self._addr_array[0])
        delegations: list = response['delegations']
        total_delegated: int = response['totalDelegated']
        self.assertEqual(0, len(delegations))
        self.assertEqual(0, total_delegated)

    def test_delegation(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # gain 10 icx
        balance: int = 10 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # stake 10 icx
        stake: int = balance
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

        # get delegation
        response: dict = self.get_delegation(self._addr_array[0])
        expected_response: list = [{"address": address, "value": value} for (address, value) in delegations]
        self.assertEqual(expected_response, response["delegations"])
        self.assertEqual(total_delegating, response["totalDelegated"])

        # other delegation 1 icx addr10 ~ addr19
        delegation_amount: int = 1 * ICX_IN_LOOP
        total_delegating: int = 0
        delegations: list = []
        start_index: int = 10
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

        # get delegation
        response: dict = self.get_delegation(self._addr_array[0])
        expected_response: list = [{"address": address, "value": value} for (address, value) in delegations]
        self.assertEqual(expected_response, response["delegations"])
        self.assertEqual(total_delegating, response["totalDelegated"])
