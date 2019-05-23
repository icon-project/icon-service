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
from typing import TYPE_CHECKING, Any, Union

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, IconScoreException
from iconservice.icon_constant import ConfigKey
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase, LATEST_GOVERNANCE

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployAudit(TestIntegrateBase):
    """
    audit on
    test governance deploy audit accept, reject
    """

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def _update_governance(self) -> bytes:
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_hash1 = tx_results[0].tx_hash
        self._accept_score(tx_hash1)
        return tx_hash1

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
        self.assertEqual(expect_status, response)

    def _deploy_score(self, score_path: str, value: int, update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("sample_deploy_scores",
                                  score_path,
                                  self._addr_array[0],
                                  address,
                                  deploy_params={'value': hex(value * self._icx_factor)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _accept_score(self, tx_hash: Union[bytes, str]):
        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'acceptScore',
                                      {"txHash": tx_hash_str})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _reject_score(self, tx_hash: Union[bytes, str], reason: str):
        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'rejectScore',
                                      {"txHash": tx_hash_str,
                                       "reason": reason})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_governance_call_about_add_auditor_already_auditor(self):
        eoa_addr = create_address()
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

    def test_governance_call_about_add_auditor_already_auditor_update_governance(self):
        self._update_governance()

        eoa_addr = create_address()
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid address: already auditor")

    def test_governance_call_about_add_remove_auditor_invalid_address(self):
        self._update_governance()

        raise_exception_start_tag("addAuditor")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str("")})
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_result.failure.message, "Invalid address")

        raise_exception_start_tag("removeAuditor")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str("")})
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_result.failure.message, "Invalid address")

    def test_governance_call_about_add_remove_auditor_score_addr(self):
        # Wrong pass!
        # have to deny into SCORE Address

        score_addr = create_address(1)

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

    def test_governance_call_about_add_remove_auditor_score_addr_update_governance(self):
        self._update_governance()

        score_addr = create_address(1)

        raise_exception_start_tag("addAuditor")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid EOA Address: {str(score_addr)}")

        raise_exception_start_tag("removeAuditor")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid EOA Address: {str(score_addr)}")

    def test_governance_call_about_add_remove_auditor_not_owner(self):
        eoa_addr = create_address()

        raise_exception_start_tag("addAuditor")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeAuditor")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_add_remove_auditor_not_owner_update_governance(self):
        self._update_governance()

        eoa_addr = create_address()

        raise_exception_start_tag("addAuditor")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeAuditor")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_remove_auditor_not_yourself(self):
        self._update_governance()

        eoa_addr = create_address()

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addAuditor',
                                        {"address": str(self._addr_array[0])})
        self.assertEqual(tx_result.status, int(True))

        raise_exception_start_tag("removeAuditor")
        tx_result = self._external_call(eoa_addr,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeAuditor',
                                        {"address": str(self._addr_array[0])})
        raise_exception_end_tag("removeAuditor")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not yourself")

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

        tx_hash1 = self._update_governance()

        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1
            }
        }
        self._assert_get_score_status(GOVERNANCE_SCORE_ADDRESS, expect_ret)

    def test_normal_score(self):
        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_normal_score_update_governance(self):
        self._update_governance()

        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

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
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : empty str
        raise_exception_start_tag("Invalid txHash")
        tx_result = self._accept_score("")
        raise_exception_end_tag("Invalid txHash")
        self.assertEqual(tx_result.status, int(False))

    def test_normal_score_fail1_fix_update_governance(self):
        self._update_governance()

        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : empty str
        raise_exception_start_tag("Invalid txHash")
        tx_result = self._accept_score("")
        raise_exception_end_tag("Invalid txHash")
        self.assertEqual(tx_result.status, int(False))

    # call acceptScore with the second latest pending deploy txHash
    def test_normal_score_fail2(self):
        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._deploy_score("update/sample_score", 3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid update tx_hash")
        tx_result = self._accept_score(tx_hash3)
        raise_exception_end_tag("Invalid update tx_hash")
        self.assertEqual(tx_result.status, int(False))

    def test_normal_score_fail2_fix_update_governance(self):
        self._update_governance()

        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._deploy_score("update/sample_score", 3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid update tx_hash")
        tx_result = self._accept_score(tx_hash3)
        raise_exception_end_tag("Invalid update tx_hash")
        self.assertEqual(tx_result.status, int(False))

    # call acceptScore with the deploy txHash of active SCORE
    def test_normal_score_fail3(self):
        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. duplicated accept SCORE : tx_hash1
        raise_exception_start_tag("Invalid status: no next status")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_start_tag("Invalid status: no next status")
        self.assertEqual(tx_result.status, int(False))

    def test_normal_score_fail3_fix_update_governance(self):
        self._update_governance()

        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. duplicated accpt SCORE : tx_hash1
        raise_exception_start_tag("Invalid status: no next status")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_start_tag("Invalid status: no next status")
        self.assertEqual(tx_result.status, int(False))

    # call acceptScore with the deploy txHash of SCORE which was active
    def test_normal_score_fail4(self):
        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._deploy_score("update/sample_score", 3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid update tx_hash")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("Invalid update tx_hash")
        self.assertEqual(tx_result.status, int(False))

        # Error due to above effect
        # 6. accept SCORE : tx_hash4
        raise_exception_start_tag("wrong case")
        tx_result = self._accept_score(tx_hash4)
        raise_exception_end_tag("wrong case")
        self.assertEqual(tx_result.status, int(False))

    def test_normal_score_fail4_fix_update_governance(self):
        self._update_governance()

        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accept SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._deploy_score("update/sample_score", 3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid update tx_hash")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("Invalid update tx_hash")
        self.assertEqual(tx_result.status, int(False))

        # Fix
        # 6. accept SCORE : tx_hash4
        tx_result = self._accept_score(tx_hash4)
        self.assertEqual(tx_result.status, int(True))

    # call acceptScore with the already rejected deploy txHash
    def test_normal_score_fail5(self):
        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._reject_score(tx_hash3, "hello!")
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid status: next is rejected")
        tx_result = self._accept_score(tx_hash3)
        self.assertEqual(tx_result.status, int(False))
        raise_exception_end_tag("Invalid status: next is rejected")

    def test_normal_score_fail5_fix_update_governance(self):
        self._update_governance()

        # 1. deploy (wait audit)
        tx_result = self._deploy_score("install/sample_score", 1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}

        # assert SCORE status
        self._assert_get_score_status(score_addr1, expect_ret)

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. update (wait audit)
        tx_result = self._deploy_score("update/sample_score", 2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

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
        tx_result = self._reject_score(tx_hash3, "hello!")
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

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
        raise_exception_start_tag("Invalid status: next is rejected")
        tx_result = self._accept_score(tx_hash3)
        self.assertEqual(tx_result.status, int(False))
        raise_exception_end_tag("Invalid status: next is rejected")


if __name__ == '__main__':
    unittest.main()
