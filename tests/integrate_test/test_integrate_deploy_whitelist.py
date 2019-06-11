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

import unittest
from typing import TYPE_CHECKING, Any

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase, LATEST_GOVERNANCE

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployWhiteList(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: True}}

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  LATEST_GOVERNANCE,
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _assert_get_score_status(self, target_addr: 'Address', expect_status: dict):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def _deploy_score(self,
                      from_addr: 'Address',
                      score_root_path: str,
                      score_path: str,
                      value: int,
                      update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx(score_root_path,
                                  score_path,
                                  from_addr,
                                  address,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_governance_call_about_add_deployer_already_deployer(self):
        eoa_addr = create_address()
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

    def test_governance_call_about_add_deployer_already_deployer_update_governance(self):
        self._update_governance()

        eoa_addr = create_address()
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid address: already deployer")

    def test_governance_call_about_add_remove_deployer_invalid_address(self):
        self._update_governance()

        raise_exception_start_tag("addDeployer")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str("")})
        raise_exception_end_tag("addDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_result.failure.message, "Invalid address")

        raise_exception_start_tag("removeDeployer")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str("")})
        raise_exception_end_tag("removeDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_result.failure.message, "Invalid address")

    def test_governance_call_about_add_remove_deployer_score_addr(self):
        # Wrong pass!
        # have to deny into SCORE Address

        score_addr = create_address(1)

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

    def test_governance_call_about_add_remove_deployer_score_addr_update_governance(self):
        self._update_governance()

        score_addr = create_address(1)

        raise_exception_start_tag("addDeployer")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("addDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid EOA Address: {str(score_addr)}")

        raise_exception_start_tag("removeDeployer")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("removeDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid EOA Address: {str(score_addr)}")

    def test_governance_call_about_add_remove_deployer_not_owner(self):
        eoa_addr = create_address()

        raise_exception_start_tag("addDeployer")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeDeployer")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_add_remove_deployer_not_owner_update_governance(self):
        self._update_governance()

        eoa_addr = create_address()

        raise_exception_start_tag("addDeployer")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeDeployer")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_remove_auditor_not_yourself(self):
        self._update_governance()

        eoa_addr = create_address()

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        raise_exception_start_tag("removeDeployer")
        tx_result = self._external_call(eoa_addr,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(self._addr_array[0])})
        raise_exception_end_tag("removeDeployer")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not yourself")

    def test_score_add_deployer(self):
        value = 1 * self._icx_factor

        with self.assertRaises(BaseException) as e:
            self._deploy_score(self._addr_array[0],
                               "test_deploy_scores",
                               "install/test_score",
                               value)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._deploy_score(self._addr_array[0],
                                       "test_deploy_scores",
                                       "install/test_score",
                                       value)

        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        expect_ret = {}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_score_add_deployer_update_governance(self):
        self._update_governance()

        value = 1 * self._icx_factor

        with self.assertRaises(BaseException) as e:
            self._deploy_score(self._addr_array[0],
                               "test_deploy_scores",
                               "install/test_score",
                               value)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._deploy_score(self._addr_array[0],
                                       "test_deploy_scores",
                                       "install/test_score",
                                       value)

        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1
            }}

        self._assert_get_score_status(score_addr1, expect_ret)

    def test_score_remove_deployer(self):
        value = 1 * self._icx_factor

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._deploy_score(self._addr_array[0],
                                       "test_deploy_scores",
                                       "install/test_score",
                                       value)

        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        expect_ret = {}

        self._assert_get_score_status(score_addr1, expect_ret)

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        with self.assertRaises(BaseException) as e:
            self._deploy_score(self._addr_array[0], "test_deploy_scores", "update/test_score", value, score_addr1)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

    def test_score_remove_deployer_update_governance(self):
        self._update_governance()

        value = 1 * self._icx_factor

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._deploy_score(self._addr_array[0],
                                       "test_deploy_scores",
                                       "install/test_score",
                                       value)

        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1
            }}

        self._assert_get_score_status(score_addr1, expect_ret)

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeDeployer',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        with self.assertRaises(BaseException) as e:
            self._deploy_score(self._addr_array[0], "test_deploy_scores", "update/test_score", value, score_addr1)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))


if __name__ == '__main__':
    unittest.main()
