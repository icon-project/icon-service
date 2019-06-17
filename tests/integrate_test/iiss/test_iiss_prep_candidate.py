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
from copy import deepcopy
from typing import TYPE_CHECKING

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_MAX_DELEGATIONS
from iconservice.icon_constant import REV_IISS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegratePRep(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision: int):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                       {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})

        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)

        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})

        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _reg_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value: str = data[ConstantKeys.PUBLIC_KEY].hex()
        data[ConstantKeys.PUBLIC_KEY] = value
        value: str = hex(data[ConstantKeys.INCENTIVE_REP])
        data[ConstantKeys.INCENTIVE_REP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _set_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value = data.get(ConstantKeys.INCENTIVE_REP)
        if value:
            data[ConstantKeys.INCENTIVE_REP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', data)
        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _unreg_prep(self, address: 'Address'):

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRep', {})
        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def test_iiss_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        data: dict = {
            ConstantKeys.NAME: "name",
            ConstantKeys.EMAIL: "email",
            ConstantKeys.WEBSITE: "website",
            ConstantKeys.DETAILS: "json",
            ConstantKeys.P2P_END_POINT: "ip",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.INCENTIVE_REP: 200
        }
        self._reg_prep(self._addr_array[0], data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }

        response = self._query(query_request)
        expected_response: dict = data

        self.assertEqual(expected_response[ConstantKeys.NAME], response[ConstantKeys.NAME])
        self.assertEqual(expected_response[ConstantKeys.EMAIL], response[ConstantKeys.EMAIL])
        self.assertEqual(expected_response[ConstantKeys.WEBSITE], response[ConstantKeys.WEBSITE])
        self.assertEqual(expected_response[ConstantKeys.DETAILS], response[ConstantKeys.DETAILS])
        self.assertEqual(expected_response[ConstantKeys.P2P_END_POINT], response[ConstantKeys.P2P_END_POINT])
        self.assertEqual(expected_response[ConstantKeys.PUBLIC_KEY], response[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(expected_response[ConstantKeys.INCENTIVE_REP], response[ConstantKeys.INCENTIVE_REP])

        data: dict = {
            ConstantKeys.INCENTIVE_REP: 2001,
        }
        self._set_prep(self._addr_array[0], data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }

        response = self._query(query_request)

        self.assertEqual(ConstantKeys.NAME, response[ConstantKeys.NAME])
        self.assertEqual(ConstantKeys.WEBSITE, response[ConstantKeys.WEBSITE])
        self.assertEqual(hex(2001), hex(response[ConstantKeys.INCENTIVE_REP]))

        self._unreg_prep(self._addr_array[0])

    def test_iiss_prep_candidate_list(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        for i in range(10):
            data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
                ConstantKeys.INCENTIVE_REP: 200+i
            }
            self._reg_prep(self._addr_array[i], data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                }
            }
        }

        response = self._query(query_request)
        self.assertEqual(0, response["totalDelegated"])
        actual_list: list = response["preps"]
        for i, actual_prep in enumerate(actual_list):
            self.assertEqual(self._addr_array[i], actual_prep["address"])
            self.assertEqual(0, actual_prep["delegated"])

    def test_iiss_prep_candidate_list_and_delegated(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        for i in range(10):
            data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
                ConstantKeys.INCENTIVE_REP: 200+i
            }
            self._reg_prep(self._addr_array[i], data)

        # gain 10 icx
        balance: int = 10 * 10 ** 18
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                }
            }
        }

        value: int = 1 * 10 ** 18
        response = self._query(query_request)
        self.assertEqual(10 * value, response["totalDelegated"])
        actual_list: list = response["preps"]
        for i, actual_prep in enumerate(actual_list):
            self.assertEqual(self._addr_array[i], actual_prep["address"])
            self.assertEqual(value, actual_prep["delegated"])

        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 0)
        tx_list = [tx]
        tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)
