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

"""on_install parameters testcase"""

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateOnInstallParameters(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                       {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def test_oninstall_parameters_success(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

    def test_more_parameters_oninstall(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12",
                                                                      "additional_param": hex(123)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("on_install() got an unexpected keyword argument "
                                                           "'additional_param'") != -1)
        self.assertEqual(tx_results[0].status, int(False))

    def test_missing_parameters_oninstall(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"decimal": "0x12"})
        tx2 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000)})
        tx3 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertEqual(tx_results[1].failure.code, 32000)
        self.assertEqual(tx_results[2].failure.code, 32000)

        self.assertTrue(
            tx_results[0].failure.message.find("on_install() missing 1 required positional argument:") != -1)
        self.assertTrue(
            tx_results[1].failure.message.find("on_install() missing 1 required positional argument:") != -1)
        self.assertTrue(
            tx_results[2].failure.message.find("on_install() missing 2 required positional arguments:") != -1)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[2].status, int(False))

    def test_invalid_parameter_value_oninstall(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": str(self._addr_array[0]),
                                                                      "decimal": "0x12"})

        tx2 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": str(self._addr_array[0]),
                                                                      "decimal": "0x12",
                                                                      "address_param": "0x12"})

        tx3 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000),
                                                                      "decimal": "0x12",
                                                                      "address_param": f"hx{'1234' * 5}"})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertEqual(tx_results[1].failure.code, 32000)
        self.assertEqual(tx_results[2].failure.code, 32602)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[2].status, int(False))

    def test_invalid_kwargs_parameter_value_oninstall(self):
        self._update_governance()
        self._set_revision(2)

        tx = self._make_deploy_tx("test_deploy_scores/install",
                                  "test_legacy_kwargs_params",
                                  self._addr_array[0],
                                  ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx])

        self._write_precommit_state(prev_block)

        score_addr = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
            }
        }
        self.assertEqual(self._query(query_request), "Hello")

        self._set_revision(3)

        tx = self._make_deploy_tx("test_deploy_scores/install",
                                  "test_legacy_kwargs_params",
                                  self._addr_array[0],
                                  ZERO_SCORE_ADDRESS)

        raise_exception_start_tag("test_invalid_kwargs_parameter_value_oninstall")
        prev_block, tx_results = self._make_and_req_block([tx])
        raise_exception_end_tag("test_invalid_kwargs_parameter_value_oninstall")

        self.assertEqual(tx_results[0].status, int(False))
