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
from iconservice.icon_constant import ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateDeployBlackList(TestIntegrateBase):
    def test_governance_call_about_add_blacklist_myself(self):
        self.update_governance()

        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(GOVERNANCE_SCORE_ADDRESS)},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "can't add myself")

    def test_governance_call_about_add_blacklist_already_blacklist(self):
        score_addr = create_address(1)

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
        )

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
        )

    def test_governance_call_about_add_blacklist_already_blacklist_update_governance(
        self,
    ):
        self.update_governance()

        score_addr = create_address(1)

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
        )

        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message, "Invalid address: already SCORE blacklist"
        )

    def test_governance_call_about_blacklist_invalid_address(self):
        self.update_governance()

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_invalid_address -1"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str("")},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_invalid_address -1"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_invalid_address -2"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str("")},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_invalid_address -2"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[0].failure.message, "Invalid address")

    def test_governance_call_about_blacklist_eoa_addr(self):
        eoa_addr = create_address()

        raise_exception_start_tag("test_governance_call_about_blacklist_eoa_addr -1")
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(eoa_addr)},
            expected_status=False,
        )
        raise_exception_end_tag("test_governance_call_about_blacklist_eoa_addr -1")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message, f"Invalid SCORE Address: {str(eoa_addr)}"
        )

        raise_exception_start_tag("test_governance_call_about_blacklist_eoa_addr -2")
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str(eoa_addr)},
            expected_status=False,
        )
        raise_exception_end_tag("test_governance_call_about_blacklist_eoa_addr -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_blacklist_eoa_addr_update_governance(self):
        self.update_governance()

        eoa_addr = create_address()

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_eoa_addr_update_governance -1"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(eoa_addr)},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_eoa_addr_update_governance -1"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message, f"Invalid SCORE Address: {str(eoa_addr)}"
        )

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_eoa_addr_update_governance -2"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str(eoa_addr)},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_eoa_addr_update_governance -2"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message, f"Invalid SCORE Address: {str(eoa_addr)}"
        )

    def test_governance_call_about_blacklist_not_owner(self):
        score_addr = create_address(1)

        raise_exception_start_tag("addToScoreBlackList")
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
            expected_status=False,
        )
        raise_exception_end_tag("addToScoreBlackList")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag("removeFromScoreBlackList")
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str(score_addr)},
            expected_status=False,
        )
        raise_exception_end_tag("removeFromScoreBlackList")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid address: not in list")

    def test_governance_call_about_blacklist_not_owner_update_governance(self):
        self.update_governance()

        score_addr = create_address(1)

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_not_owner_update_governance -1"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr)},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_not_owner_update_governance -1"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

        raise_exception_start_tag(
            "test_governance_call_about_blacklist_not_owner_update_governance -2"
        )
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str(score_addr)},
            expected_status=False,
        )
        raise_exception_end_tag(
            "test_governance_call_about_blacklist_not_owner_update_governance -2"
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f"Invalid sender: not owner")

    def test_score_add_blacklist(self):
        self.update_governance()

        # deploy normal SCORE
        value1 = 1
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr1 = tx_results[0].score_address

        # deploy other SCORE which has external call to normal SCORE
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_internal_call_scores",
            score_name="sample_link_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr2 = tx_results[0].score_address

        # link interface SCORE setting
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr2,
            func_name="add_score_func",
            params={"score_addr": str(score_addr1)},
        )

        # add blacklist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr1)},
        )

        # direct external call
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": score_addr1,
            "dataType": "call",
            "data": {"method": "get_value", "params": {}},
        }
        with self.assertRaises(AccessDeniedException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

        value2 = 2
        with self.assertRaises(AccessDeniedException) as e:
            self.create_score_call_tx(
                from_=self._accounts[0],
                to_=score_addr1,
                func_name="set_value",
                params={"value": hex(value2)},
            )
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

        # indirect external call
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": score_addr2,
            "dataType": "call",
            "data": {"method": "get_value", "params": {}},
        }
        with self.assertRaises(AccessDeniedException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

    def test_score_add_blacklist_not_version_field(self):
        self.update_governance()

        # deploy normal SCORE
        value1 = 1
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr1 = tx_results[0].score_address

        # deploy other SCORE which has external call to normal SCORE
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_internal_call_scores",
            score_name="sample_link_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr2 = tx_results[0].score_address

        # link interface SCORE setting
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr2,
            func_name="add_score_func",
            params={"score_addr": str(score_addr1)},
        )

        # add blacklist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr1)},
        )

        # direct external call
        query_request = {
            "from": self._accounts[0],
            "to": score_addr1,
            "dataType": "call",
            "data": {"method": "get_value", "params": {}},
        }
        with self.assertRaises(AccessDeniedException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

        value2 = 2 * ICX_IN_LOOP
        with self.assertRaises(AccessDeniedException) as e:
            self.create_score_call_tx(
                from_=self._accounts[0],
                to_=score_addr1,
                func_name="set_value",
                params={"value": hex(value2)},
            )
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

        # indirect external call
        query_request = {
            "from": self._accounts[0],
            "to": score_addr2,
            "dataType": "call",
            "data": {"method": "get_value", "params": {}},
        }
        with self.assertRaises(AccessDeniedException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)

    def test_score_remove_deployer(self):
        self.update_governance()

        # deploy normal SCORE
        value1 = 1
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr1 = tx_results[0].score_address

        # add blacklist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addToScoreBlackList",
            params={"address": str(score_addr1)},
        )

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeFromScoreBlackList",
            params={"address": str(score_addr1)},
        )

        # access query external call in prev blacklist SCORE
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {"method": "get_value", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, value1 * ICX_IN_LOOP)

        # access external call in prev blacklist SCORE
        value2 = 2
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr1,
            func_name="set_value",
            params={"value": hex(value2 * ICX_IN_LOOP)},
        )

        # access query external call in prev blacklist SCORE
        response = self._query(query_request)
        self.assertEqual(response, value2 * ICX_IN_LOOP)
