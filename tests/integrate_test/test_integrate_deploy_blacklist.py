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

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployBlackList(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_4/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _deploy_score(self, from_addr: 'Address', score_root_path: str, score_path: str, value: int) -> Any:
        tx = self._make_deploy_tx(score_root_path,
                                  score_path,
                                  from_addr,
                                  ZERO_SCORE_ADDRESS,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_governance_call_about_add_blacklist_myself(self):
        self._update_governance()
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(GOVERNANCE_SCORE_ADDRESS)})
        self.assertEqual(tx_result.status, int(False))

    def test_governance_call_about_add_blacklist_already_blacklist(self):
        score_addr = create_address(1)
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

    def test_governance_call_about_add_blacklist_already_blacklist_update_governance(self):
        self._update_governance()

        score_addr = create_address(1)
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(True))

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid address: already SCORE blacklist")

    def test_governance_call_about_blacklist_invalid_address(self):
        self._update_governance()

        raise_exception_start_tag("addToScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str("")})
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(tx_result.failure.message, "Invalid address")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str("")})
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(tx_result.failure.message, "Invalid address")

    def test_governance_call_about_blacklist_eoa_addr(self):
        eoa_addr = create_address()

        raise_exception_start_tag("addToScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid SCORE Address: {str(eoa_addr)}")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_blacklist_eoa_addr_update_governance(self):
        self._update_governance()

        eoa_addr = create_address()

        raise_exception_start_tag("addToScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid SCORE Address: {str(eoa_addr)}")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str(eoa_addr)})
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid SCORE Address: {str(eoa_addr)}")

    def test_governance_call_about_blacklist_not_owner(self):
        score_addr = create_address(1)

        raise_exception_start_tag("addToScoreBlackList")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid address: not in list")

    def test_governance_call_about_blacklist_not_owner_update_governance(self):
        self._update_governance()

        score_addr = create_address(1)

        raise_exception_start_tag("addToScoreBlackList")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str(score_addr)})
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, f"Invalid sender: not owner")

    def test_score_add_blacklist(self):
        self._update_governance()

        # deploy normal SCORE
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score(self._addr_array[0], "test_deploy_scores", "install/test_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        # deploy other SCORE which has external call to normal SCORE
        tx_result = self._deploy_score(self._addr_array[0], "test_internal_call_scores", "test_link_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr2 = tx_result.score_address

        # link interface SCORE setting
        tx_result = self._external_call(self._addr_array[0],
                                        score_addr2,
                                        'add_score_func',
                                        {"score_addr": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # add blacklist
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # direct external call
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        value2 = 2 * self._icx_factor
        with self.assertRaises(BaseException) as e:
            self._make_score_call_tx(self._addr_array[0],
                                     score_addr1,
                                     'set_value',
                                     {"value": hex(value2)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        # indirect external call
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

    def test_score_add_blacklist_not_version_field(self):
        self._update_governance()

        # deploy normal SCORE
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score(self._addr_array[0], "test_deploy_scores", "install/test_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        # deploy other SCORE which has external call to normal SCORE
        tx_result = self._deploy_score(self._addr_array[0], "test_internal_call_scores", "test_link_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr2 = tx_result.score_address

        # link interface SCORE setting
        tx_result = self._external_call(self._addr_array[0],
                                        score_addr2,
                                        'add_score_func',
                                        {"score_addr": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # add blacklist
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # direct external call
        query_request = {
            "from": self._addr_array[0],
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        value2 = 2 * self._icx_factor
        with self.assertRaises(BaseException) as e:
            self._make_score_call_tx(self._addr_array[0],
                                     score_addr1,
                                     'set_value',
                                     {"value": hex(value2)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        # indirect external call
        query_request = {
            "from": self._addr_array[0],
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

    def test_score_remove_deployer(self):
        self._update_governance()

        # deploy normal SCORE
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score(self._addr_array[0], "test_deploy_scores", "install/test_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        # add blacklist
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addToScoreBlackList',
                                        {"address": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # remove blacklist
        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeFromScoreBlackList',
                                        {"address": str(score_addr1)})
        self.assertEqual(tx_result.status, int(True))

        # access query external call in prev blacklist SCORE
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value1)

        # access external call in prev blacklist SCORE
        value2 = 2 * self._icx_factor
        tx_result = self._external_call(self._addr_array[0],
                                        score_addr1,
                                        'set_value',
                                        {"value": hex(value2)})
        self.assertEqual(tx_result.status, int(True))

        # access query external call in prev blacklist SCORE
        response = self._query(query_request)
        self.assertEqual(response, value2)


if __name__ == '__main__':
    unittest.main()
