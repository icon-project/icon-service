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

import random
import unittest
from copy import deepcopy

from iconservice import Address
from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_MAX_DELEGATIONS, REV_IISS
from tests import create_address
from tests.integrate_test import create_register_prep_params
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateIISS(TestIntegrateBase):
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

    def _reg_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        data[ConstantKeys.PUBLIC_KEY] = data[ConstantKeys.PUBLIC_KEY].hex()

        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'registerPRep',
                                      data)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_reg_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        count = 200
        for i in range(count):
            reg_data: dict = create_register_prep_params(i)
            self._reg_prep(create_address(), reg_data)

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
        preps: list = response['preps']
        total_delegated: int = response['totalDelegated']
        # TODO setting trigger!
        self.assertEqual(200, len(preps))
        self.assertEqual(0, total_delegated)

    def test_total(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        # prep register

        count = 5
        for i in range(count):
            reg_data: dict = create_register_prep_params(i)
            self._reg_prep(self._addr_array[i + 10], reg_data)

        # gain 10 icx (addr0 - 5)
        balance: int = 10 * 10 ** 18
        for i in range(5):
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[i], balance)
            prev_block, tx_results = self._make_and_req_block([tx])
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
        self._query(query_request)

        self._make_and_req_block([])
        self._make_and_req_block([])
        self._make_and_req_block([])
        self._make_and_req_block([])

    def test_ise_IISS(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getIISSInfo",
                "params": {
                }
            }
        }

        response = self._query(query_request)

        expected_response = {
            "variable": {
                "irep": 10000,
                "rrep": 800
            }
        }
        self.assertEqual(expected_response, response)


if __name__ == '__main__':
    unittest.main()
