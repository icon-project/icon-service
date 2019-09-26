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
from typing import List, Dict

from iconservice.base.address import ZERO_SCORE_ADDRESS, Address
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REVISION, ICX_IN_LOOP
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSDelegate(TestIISSBase):

    def test_delegations_with_duplicated_addresses(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # stake 10 icx
        stake: int = 10 * ICX_IN_LOOP
        self.set_stake(from_=self._accounts[0],
                       value=stake)

        # delegate 1 icx to the same addr1 10 times in one request
        delegations: list = []
        delegation_amount: int = 1 * ICX_IN_LOOP
        for i in range(IISS_MAX_DELEGATIONS):
            delegation_info: tuple = \
                (
                    self._accounts[1],
                    delegation_amount
                )
            delegations.append(delegation_info)

        # setDelegation request will be failed due to duplicated addresses
        tx_results: List['TransactionResult'] = self.set_delegation(from_=self._accounts[0],
                                                                    origin_delegations=delegations,
                                                                    expected_status=False)
        self.assertEqual(ExceptionCode.INVALID_PARAMETER, tx_results[0].failure.code)

        # get delegation
        response: dict = self.get_delegation(self._accounts[0])
        delegations: list = response['delegations']
        total_delegated: int = response['totalDelegated']
        self.assertEqual(0, len(delegations))
        self.assertEqual(0, total_delegated)

    def test_delegation(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

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

        # get delegation
        response: dict = self.get_delegation(self._accounts[0])
        expected_response: list = [{"address": account.address,
                                    "value": value} for (account, value) in delegations]
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
                    self._accounts[start_index + i],
                    delegation_amount
                )
            delegations.append(delegation_info)
            total_delegating += delegation_amount

        self.set_delegation(from_=self._accounts[0],
                            origin_delegations=delegations)

        # get delegation
        response: dict = self.get_delegation(self._accounts[0])
        expected_response: list = [{"address": account.address,
                                    "value": value} for (account, value) in delegations]
        self.assertEqual(expected_response, response["delegations"])
        self.assertEqual(total_delegating, response["totalDelegated"])

    def test_delegation_invalid_params(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # stake 10 icx
        stake: int = 10 * ICX_IN_LOOP
        self.set_stake(from_=self._accounts[0],
                       value=stake)

        # set delegation 1
        delegations: list = [(self._accounts[0], 1)]
        delegations: List[Dict[str, str]] = self.create_delegation_params(delegations)
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="setDelegation",
                                             params={"invalid": delegations})
        self.process_confirm_block_tx([tx], expected_status=False)

        # set delegation 2
        delegations: list = [(self._accounts[0], 1)]
        delegations: List[Dict[str, str]] = self.create_delegation_params(delegations)
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="setDelegation",
                                             params={
                                                 "delegations": delegations,
                                                 "delegations2": []
                                             })
        self.process_confirm_block_tx([tx], expected_status=False)

        # set delegation 3
        delegations: list = [(self._accounts[0], 1)]
        delegations: List[Dict[str, str]] = self.create_delegation_params(delegations)
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="setDelegation",
                                             params={
                                                 "delegations1": delegations,
                                                 "delegations2": []
                                             })
        self.process_confirm_block_tx([tx], expected_status=False)

        # set delegation 3
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="setDelegation",
                                             params={})
        self.process_confirm_block_tx([tx])

