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
from iconservice.base.exception import InvalidParamsException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import REV_IISS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegratePrep(TestIntegrateBase):

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

    def _reg_candidate(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value: str = hex(data[ConstantKeys.GOVERNANCE_VARIABLE][ConstantKeys.INCENTIVE_REP])
        data[ConstantKeys.GOVERNANCE_VARIABLE][ConstantKeys.INCENTIVE_REP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRepCandidate', data)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_candidate(self, address: 'Address', data: dict):

        data = deepcopy(data)
        governance_data = data.get(ConstantKeys.GOVERNANCE_VARIABLE)
        if governance_data:
            value = governance_data.get(ConstantKeys.INCENTIVE_REP)
            if value:
                governance_data[ConstantKeys.INCENTIVE_REP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRepCandidate', data)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _unreg_candidate(self, address: 'Address'):

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRepCandidate', {})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_reg_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: 200
            }
        }
        self._reg_candidate(self._addr_array[0], reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepCandidate",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(reg_data, response)

    def test_set_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: 200
            }
        }
        self._reg_candidate(self._addr_array[0], reg_data)

        update_data: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: 300,
            }
        }
        self._set_candidate(self._addr_array[0], update_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepCandidate",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        expected: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: 300
            }
        }
        self.assertEqual(expected, response)

    def test_unreg_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: 200
            }
        }
        self._reg_candidate(self._addr_array[0], reg_data)
        self._unreg_candidate(self._addr_array[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepCandidate",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual(f'Failed to get candidate: no register', e.exception.args[0])

    def test_prep_list(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        for i in range(10):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.GOVERNANCE_VARIABLE: {
                    ConstantKeys.INCENTIVE_REP: 200 + i
                }
            }
            self._reg_candidate(self._addr_array[i], reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['prepList']

        self.assertEqual(0, total_delegated)
        self.assertEqual(0, len(prep_list))
