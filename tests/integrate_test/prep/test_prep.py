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
from tests.integrate_test import create_register_prep_params
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


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
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _stake(self, address: 'Address', value: int, _revision: int = REV_IISS):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list, _revision: int = REV_IISS):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})

        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _reg_prep(self, address: 'Address', data: dict, _revision: int = REV_IISS):

        data = deepcopy(data)
        data[ConstantKeys.PUBLIC_KEY] = f"0x{data[ConstantKeys.PUBLIC_KEY].hex()}"

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual('PRepRegistered(Address)', tx_results[0].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[0].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _set_prep(self, address: 'Address', data: dict, _revision: int = REV_IISS):

        data = deepcopy(data)
        value = data.get(ConstantKeys.IREP)
        if value:
            data[ConstantKeys.IREP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', data)
        prev_block, tx_results = self._make_and_req_block([tx])

        tx_result: 'TransactionResult' = tx_results[0]

        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual('PRepSet(Address)', tx_result.event_logs[0].indexed[0])
        self.assertEqual(address, tx_result.event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _unreg_prep(self, address: 'Address', _revision: int = REV_IISS):

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRep', {})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual('PRepUnregistered(Address)', tx_results[0].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[0].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def test_reg_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = create_register_prep_params(index=0)
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

    def test_set_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = create_register_prep_params(index=0)
        self._reg_prep(self._addr_array[0], reg_data)

        update_data: dict = {
            ConstantKeys.NAME: "banana",
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

    def test_unregister_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        address: 'Address' = self._addr_array[0]

        reg_data: dict = create_register_prep_params(index=0)
        self._reg_prep(address, reg_data)
        self._unreg_prep(address)

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
            self._query(query_request)
        self.assertEqual(f"P-Rep not found: {str(address)}", e.exception.args[0])

        # Unregister a non-existing P-Rep
        address: 'Address' = self._addr_array[1]
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, "unregisterPRep", {})
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result: 'TransactionResult' = tx_results[0]

        self.assertEqual(0, tx_result.status)
        self.assertIsNotNone(tx_result.failure)
        self.assertEqual(prev_block.height, tx_result.block_height)
        self.assertEqual(0, tx_result.tx_index)
        self.assertIsNone(tx_result.score_address)

    def test_prep_list(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        for i in range(10):
            reg_data: dict = create_register_prep_params(i)
            self._reg_prep(self._addr_array[i], reg_data)

            query_request = {
                "version": self._version,
                "from": self._addr_array[i],
                "to": ZERO_SCORE_ADDRESS,
                "dataType": "call",
                "data": {
                    "method": "getPRepList"
                }
            }
            response = self._query(query_request)
            total_delegated: int = response['totalDelegated']
            prep_list: list = response['preps']

            self.assertEqual(0, total_delegated)
            self.assertEqual(i+1, len(prep_list))
