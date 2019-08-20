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

from typing import TYPE_CHECKING, List

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, AccessDeniedException
from iconservice.icon_constant import ConfigKey, ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateDeployWhiteList(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: True}}

    def _assert_get_score_status(self, target_addr: 'Address', expect_status: dict):
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def test_governance_call_about_add_deployer_already_deployer(self):
        eoa_addr = create_address()

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={"address": str(eoa_addr)})
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={"address": str(eoa_addr)})

    def test_governance_call_about_add_deployer_already_deployer_update_governance(self):
        self.update_governance()

        eoa_addr = create_address()
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={"address": str(eoa_addr)})
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addDeployer",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid address: already deployer")

    def test_governance_call_about_add_remove_deployer_invalid_address(self):
        self.update_governance()

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_invalid_address -1")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addDeployer",
                                                                params={"address": str("")},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_invalid_address -1")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_invalid_address -2")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeDeployer",
                                                                params={"address": str("")},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_invalid_address -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

    def test_governance_call_about_add_remove_deployer_score_addr(self):
        # Wrong pass!
        # have to deny into SCORE Address

        score_addr = create_address(1)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={"address": str(score_addr)})
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="removeDeployer",
                        params={"address": str(score_addr)})

    def test_governance_call_about_add_remove_deployer_score_addr_update_governance(self):
        self.update_governance()

        score_addr = create_address(1)

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_score_addr_update_governance -1")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addDeployer",
                                                                params={"address": str(score_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_score_addr_update_governance -1")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid EOA Address: {str(score_addr)}")

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_score_addr_update_governance -2")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeDeployer",
                                                                params={"address": str(score_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_score_addr_update_governance -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid EOA Address: {str(score_addr)}")

    def test_governance_call_about_add_remove_deployer_not_owner(self):
        eoa_addr = create_address()

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_not_owner -1")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addDeployer",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_not_owner -1")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_not_owner -2")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeDeployer",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_not_owner -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_add_remove_deployer_not_owner_update_governance(self):
        self.update_governance()

        eoa_addr = create_address()

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_not_owner_update_governance -1")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addDeployer",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_not_owner_update_governance -1")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("test_governance_call_about_add_remove_deployer_not_owner_update_governance -2")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeDeployer",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_add_remove_deployer_not_owner_update_governance -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_remove_auditor_not_yourself(self):
        self.update_governance()

        eoa_addr = create_address()

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })
        raise_exception_start_tag("test_governance_call_about_remove_auditor_not_yourself")
        tx_results: List['TransactionResult'] = self.score_call(from_=eoa_addr,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeDeployer",
                                                                params={
                                                                    "address": str(self._accounts[0].address)
                                                                },
                                                                expected_status=False)
        raise_exception_end_tag("test_governance_call_about_remove_auditor_not_yourself")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not yourself")

    def test_score_add_deployer(self):
        value = 1

        with self.assertRaises(AccessDeniedException) as e:
            self.deploy_score(score_root="sample_deploy_scores",
                              score_name="install/sample_score",
                              from_=self._accounts[0],
                              deploy_params={"value": hex(value * ICX_IN_LOOP)})
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={"value": hex(value * ICX_IN_LOOP)})

        score_addr1 = tx_results[0].score_address

        expect_ret = {}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_score_add_deployer_update_governance(self):
        self.update_governance()

        value = 1

        with self.assertRaises(AccessDeniedException) as e:
            self.deploy_score(score_root="sample_deploy_scores",
                              score_name="install/sample_score",
                              from_=self._accounts[0],
                              deploy_params={"value": hex(value * ICX_IN_LOOP)})
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={"value": hex(value * ICX_IN_LOOP)})

        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1
            }}

        self._assert_get_score_status(score_addr1, expect_ret)

    def test_score_remove_deployer(self):
        value = 1

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={"value": hex(value * ICX_IN_LOOP)})

        score_addr1 = tx_results[0].score_address
        expect_ret = {}

        self._assert_get_score_status(score_addr1, expect_ret)

        self.score_call(from_=self._accounts[0],
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="removeDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        with self.assertRaises(AccessDeniedException) as e:
            self.deploy_score(score_root="sample_deploy_scores",
                              score_name="update/sample_score",
                              from_=self._accounts[0],
                              deploy_params={"value": hex(value * ICX_IN_LOOP)},
                              to_=score_addr1)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))

    def test_score_remove_deployer_update_governance(self):
        self.update_governance()

        value = 1

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={"value": hex(value * ICX_IN_LOOP)})

        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1
            }}

        self._assert_get_score_status(score_addr1, expect_ret)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="removeDeployer",
                        params={
                            "address": str(self._accounts[0].address)
                        })

        with self.assertRaises(AccessDeniedException) as e:
            self.deploy_score(score_root="sample_deploy_scores",
                              score_name="update/sample_score",
                              from_=self._accounts[0],
                              deploy_params={"value": hex(value * ICX_IN_LOOP)},
                              to_=score_addr1)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertTrue(e.exception.message.startswith("Invalid deployer: no permission"))
