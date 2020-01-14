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

from typing import TYPE_CHECKING, List, Optional

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, IconScoreException
from iconservice.icon_constant import ConfigKey, ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateDeployAudit(TestIntegrateBase):
    """
    audit on
    test governance deploy audit accept, reject
    """

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

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
        self.assertEqual(expect_status, response)

    def _deploy_score(self,
                      score_path: str,
                      value: int,
                      expected_status: bool = True,
                      to_: Optional['Address'] = ZERO_SCORE_ADDRESS) -> List['TransactionResult']:
        return self.deploy_score(score_root="sample_deploy_scores",
                                 score_name=score_path,
                                 from_=self._accounts[0],
                                 deploy_params={'value': hex(value * ICX_IN_LOOP)},
                                 expected_status=expected_status,
                                 to_=to_)

    def _update_governance_score(self, version: str = "latest_version"):
        tx_results: List['TransactionResult'] = self.update_governance(version=version)
        self.accept_score(tx_results[0].tx_hash)

    def test_governance_call_about_add_auditor_already_auditor(self):
        eoa_addr = create_address()

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addAuditor",
                        params={"address": str(eoa_addr)})

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addAuditor",
                        params={"address": str(eoa_addr)})

    def test_governance_call_about_add_auditor_already_auditor_update_governance(self):
        self._update_governance_score()

        eoa_addr = create_address()
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addAuditor",
                        params={"address": str(eoa_addr)})

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addAuditor",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid address: already auditor")

    def test_governance_call_about_add_remove_auditor_invalid_address(self):
        self._update_governance_score()

        raise_exception_start_tag("addAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addAuditor",
                                                                params={"address": str("")},
                                                                expected_status=False)
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

        raise_exception_start_tag("removeAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeAuditor",
                                                                params={"address": str("")},
                                                                expected_status=False)
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

    def test_governance_call_about_add_remove_auditor_score_addr(self):
        # Wrong pass!
        # have to deny into SCORE Address

        score_addr = create_address(1)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addAuditor",
                        params={"address": str(score_addr)})

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="removeAuditor",
                        params={"address": str(score_addr)})

    def test_governance_call_about_add_remove_auditor_score_addr_update_governance(self):
        self._update_governance_score()

        score_addr = create_address(1)

        raise_exception_start_tag("addAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addAuditor",
                                                                params={"address": str(score_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid EOA Address: {str(score_addr)}")

        raise_exception_start_tag("removeAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeAuditor",
                                                                params={"address": str(score_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid EOA Address: {str(score_addr)}")

    def test_governance_call_about_add_remove_auditor_not_owner(self):
        eoa_addr = create_address()

        raise_exception_start_tag("addAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addAuditor",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeAuditor",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_add_remove_auditor_not_owner_update_governance(self):
        self._update_governance_score()

        eoa_addr = create_address()

        raise_exception_start_tag("addAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="addAuditor",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeAuditor")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeAuditor",
                                                                params={"address": str(eoa_addr)},
                                                                expected_status=False)
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_remove_auditor_not_yourself(self):
        self._update_governance_score()

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="addAuditor",
                        params={"address": str(self._accounts[0].address)})

        raise_exception_start_tag("removeAuditor")
        eoa_addr = create_address()
        tx_results: List['TransactionResult'] = self.score_call(from_=eoa_addr,
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name="removeAuditor",
                                                                params={
                                                                    "address":
                                                                        str(self._accounts[0].address)
                                                                },
                                                                expected_status=False)
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not yourself")

    def test_builtin_score(self):
        expect_ret = {
            'current': {
                'status': 'active'}
        }
        with self.assertRaises(IconScoreException) as e:
            self._assert_get_score_status(GOVERNANCE_SCORE_ADDRESS, expect_ret)
        self.assertEqual(e.exception.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(e.exception.message, "SCORE not found")

    def test_builtin_score_update_governance(self):
        """
        Test calling getScoreStatus() for governance SCORE in the case that audit is on

        - A return value of Normal SCORE and Governance has the same format.
        - For example, the return value of Governance should be
            {"current": {"status": "active"}}.
        """

        tx_results: List['TransactionResult'] = self.update_governance()
        self.accept_score(tx_results[0].tx_hash)

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_results[0].tx_hash
            }
        }
        self._assert_get_score_status(GOVERNANCE_SCORE_ADDRESS, expect_ret)

    def test_normal_score(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2 = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_normal_score_update_governance(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2 = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

    # call acceptScore with non - existing deploy txHash
    def test_normal_score_fail1(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : empty str
        raise_exception_start_tag("test_normal_score_fail1")
        self.accept_score("", expected_status=False)
        raise_exception_end_tag("test_normal_score_fail1")

    def test_normal_score_fail1_fix_update_governance(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : empty str
        raise_exception_start_tag("test_normal_score_fail1_fix_update_governance")
        self.accept_score("", expected_status=False)
        raise_exception_end_tag("test_normal_score_fail1_fix_update_governance")

    # call acceptScore with the second latest pending deploy txHash
    def test_normal_score_fail2(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. overwrite
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   3,
                                                                   to_=score_addr1)
        tx_hash4: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 5. accept SCORE : tx_hash4
        raise_exception_start_tag("test_normal_score_fail2")
        self.accept_score(tx_hash3, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail2")

    def test_normal_score_fail2_fix_update_governance(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. overwrite
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   3,
                                                                   to_=score_addr1)
        tx_hash4: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 5. accept SCORE : tx_hash4
        raise_exception_start_tag("test_normal_score_fail2_fix_update_governance")
        self.accept_score(tx_hash3, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail2_fix_update_governance")

    # call acceptScore with the deploy txHash of active SCORE
    def test_normal_score_fail3(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. duplicated accept SCORE : tx_hash1
        raise_exception_start_tag("test_normal_score_fail3")
        self.accept_score(tx_hash1, expected_status=False)
        raise_exception_start_tag("test_normal_score_fail3")

    def test_normal_score_fail3_fix_update_governance(self):
        self._update_governance_score()

        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. duplicated accpt SCORE : tx_hash1
        raise_exception_start_tag("test_normal_score_fail3_fix_update_governance")
        self.accept_score(tx_hash1, expected_status=False)
        raise_exception_start_tag("test_normal_score_fail3_fix_update_governance")

    # call acceptScore with the deploy txHash of SCORE which was active
    def test_normal_score_fail4(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. overwrite
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   3,
                                                                   to_=score_addr1)
        tx_hash4: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # wrong Pass! -> Bug!
        # 5. accept SCORE : tx_hash1
        raise_exception_start_tag("test_normal_score_fail4 -1")
        self.accept_score(tx_hash1, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail4 -1")

        # Error due to above effect
        # 6. accept SCORE : tx_hash4
        raise_exception_start_tag("test_normal_score_fail4 -2")
        self.accept_score(tx_hash4, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail4 -2")

    def test_normal_score_fail4_fix_update_governance(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. overwrite
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   3,
                                                                   to_=score_addr1)
        tx_hash4: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # wrong Pass! -> Bug!
        # 5. accept SCORE : tx_hash1
        raise_exception_start_tag("test_normal_score_fail4_fix_update_governance")
        self.accept_score(tx_hash1, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail4_fix_update_governance")

        # Fix
        # 6. accept SCORE : tx_hash4
        self.accept_score(tx_hash4)

    def test_normal_score_fail4_fix_update_governance_1_0_0(self):
        self._update_governance_score("1_0_0")

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. overwrite
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   3,
                                                                   to_=score_addr1)
        tx_hash4: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 6. accept SCORE : tx_hash1
        # Already Accepted
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1, expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "Invalid txHash: already accepted")

    # call acceptScore with the already rejected deploy txHash
    def test_normal_score_fail5(self):
        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. reject SCORE : tx_hash3
        tx_results: List['TransactionResult'] = self.reject_score(tx_hash3, "hello!")
        tx_hash4 = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'rejected',
                'deployTxHash': tx_hash3,
                'auditTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 5. accpt SCORE : tx_hash3
        raise_exception_start_tag("test_normal_score_fail5")
        self.accept_score(tx_hash3, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail5")

    def test_normal_score_fail5_fix_update_governance(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("install/sample_score", 1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score("update/sample_score",
                                                                   2,
                                                                   to_=score_addr1)
        tx_hash3: bytes = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 4. reject SCORE : tx_hash3
        tx_results: List['TransactionResult'] = self.reject_score(tx_hash3, "hello!")
        tx_hash4 = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'rejected',
                'deployTxHash': tx_hash3,
                'auditTxHash': tx_hash4}
        }
        self._assert_get_score_status(score_addr1, expect_ret)

        # 5. accpt SCORE : tx_hash3
        raise_exception_start_tag("test_normal_score_fail5_fix_update_governance")
        self.accept_score(tx_hash3, expected_status=False)
        raise_exception_end_tag("test_normal_score_fail5_fix_update_governance")
