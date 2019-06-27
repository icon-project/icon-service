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
from tests import create_tx_hash
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

    def _stake(self, address: 'Address', value: int, revision: int = REV_IISS):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})

        tx_list = [tx]
        if revision >= REV_IISS:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)

        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list, revision: int = REV_IISS):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})

        tx_list = [tx]
        if revision >= REV_IISS:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _reg_prep(self, address: 'Address', data: dict, revision: int = REV_IISS):

        data = deepcopy(data)
        value: str = data[ConstantKeys.PUBLIC_KEY].hex()
        data[ConstantKeys.PUBLIC_KEY] = value
        value: str = hex(data[ConstantKeys.IREP])
        data[ConstantKeys.IREP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
        tx_list = [tx]
        if revision >= REV_IISS:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepRegistered(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _set_prep(self, address: 'Address', data: dict, revision: int = REV_IISS):

        data = deepcopy(data)
        value = data.get(ConstantKeys.IREP)
        if value:
            data[ConstantKeys.IREP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', data)
        tx_list = [tx]
        if revision >= REV_IISS:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepSet(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _unreg_prep(self, address: 'Address', revision: int = REV_IISS):

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRep', {})
        tx_list = [tx]
        if revision >= REV_IISS:
            # issue tx must be exists after revision 5
            tx_list.insert(0, self._make_dummy_issue_tx())
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepUnregistered(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def test_reg_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: 200
        }
        self._reg_prep(self._addr_array[0], reg_data)

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
        register = response["registration"]
        self.assertEqual(reg_data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(reg_data[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(reg_data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(reg_data[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(reg_data[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(reg_data[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(reg_data[ConstantKeys.IREP], register[ConstantKeys.IREP])

    def test_set_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: 200
        }
        self._reg_prep(self._addr_array[0], reg_data)

        update_data: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.IREP: 300,
        }
        self._set_prep(self._addr_array[0], update_data)

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
        register = response["registration"]

        self.assertEqual(update_data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(reg_data[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(reg_data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(reg_data[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(reg_data[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(reg_data[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(update_data[ConstantKeys.IREP], register[ConstantKeys.IREP])

    def test_unreg_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: 200
        }
        self._reg_prep(self._addr_array[0], reg_data)
        self._unreg_prep(self._addr_array[0])

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

        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual(f'PRep not found: {str(self._addr_array[0])}', e.exception.args[0])

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
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: 200 + i
            }
            self._reg_prep(self._addr_array[i], reg_data)

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
        prep_list: list = response['preps']

        self.assertEqual(0, total_delegated)
        self.assertEqual(10, len(prep_list))

