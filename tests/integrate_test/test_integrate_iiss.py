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

"""Test for icon_score_base.py and icon_score_base2.py"""

import unittest
from copy import deepcopy
import random

from iconservice.base.type_converter_templates import ConstantKeys

from iconservice import Address
from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS
from iconservice.icon_constant import IISS_MAX_DELEGATIONS
from tests import create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateIISS(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
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

    def _stake(self, address: 'Address', value: int, revision: int = 5):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})

        tx_list = [tx]
        if revision >= 5:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)

        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list, revision: int = 5):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})

        tx_list = [tx]
        if revision >= 5:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _reg_candidate(self, address: 'Address', data: dict, revision: int = 5):

        data = deepcopy(data)
        value: str = hex(data[ConstantKeys.GOVERNANCE_VARIABLE][ConstantKeys.INCENTIVE_REP])
        data[ConstantKeys.GOVERNANCE_VARIABLE][ConstantKeys.INCENTIVE_REP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRepCandidate', data)
        tx_list = [tx]
        if revision >= 5:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def test_reg_prep_candidate(self):
        self._update_governance()
        self._set_revision(4)

        count = 200
        for i in range(count):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.JSON: f"json{i}",
                ConstantKeys.IP: f"ip{i}",
                ConstantKeys.GOVERNANCE_VARIABLE: {
                    ConstantKeys.INCENTIVE_REP: 200 + i
                }
            }
            self._reg_candidate(create_address(), reg_data, 4)

        self._set_revision(5)

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
        preps: list = response['prepList']
        total_delegated: int = response['totalDelegated']
        self.assertEqual(100, len(preps))
        self.assertEqual(0, total_delegated)

    def test_total(self):
        self._update_governance()
        self._set_revision(4)

        # prep register

        count = 5
        for i in range(count):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.JSON: f"json{i}",
                ConstantKeys.IP: f"ip{i}",
                ConstantKeys.GOVERNANCE_VARIABLE: {
                    ConstantKeys.INCENTIVE_REP: 200 + i
                }
            }
            self._reg_candidate(self._addr_array[i + 10], reg_data, 4)

        self._set_revision(5)

        # gain 10 icx (addr0 - 5)
        balance: int = 10 * 10 ** 18
        for i in range(5):
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[i], balance)
            # issue tx must be exists after revision 5
            issue_tx = self._make_dummy_issue_tx()
            prev_block, tx_results = self._make_and_req_block([issue_tx, tx])
            self._write_precommit_state(prev_block)

        # set stake 10 icx
        stake: int = 10 * 10 ** 18
        for i in range(5):
            self._stake(self._addr_array[i], stake)

        # delegation 1 icx
        for i in range(5):
            delegations: list = []
            delegation_amount: int = 1 * 10 ** 18
            for _ in range(IISS_MAX_DELEGATIONS):
                ran_id: int = random.randint(0, 19)
                delegation_info: dict = {
                    "address": str(self._addr_array[ran_id]),
                    "value": hex(delegation_amount)
                }
                delegations.append(delegation_info)

            self._delegate(self._addr_array[i], delegations)

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
        print(response)

        self._make_and_req_block([])
        self._make_and_req_block([])
        self._make_and_req_block([])
        self._make_and_req_block([])


if __name__ == '__main__':
    unittest.main()
