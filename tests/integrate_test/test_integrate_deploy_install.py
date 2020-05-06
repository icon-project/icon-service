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

from typing import TYPE_CHECKING, Any, List, Union, Optional

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ICX_IN_LOOP
from tests import (
    raise_exception_start_tag,
    raise_exception_end_tag,
    create_tx_hash,
    create_timestamp,
)
from tests.integrate_test.test_integrate_base import (
    TestIntegrateBase,
    DEFAULT_DEPLOY_STEP_LIMIT,
)

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateDeployInstall(TestIntegrateBase):
    def _assert_get_score_status(self, target_addr: "Address", expect_status: dict):
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)},
            },
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def _assert_get_value(
        self, from_addr: "Address", score_addr: "Address", func_name: str, value: Any
    ):
        query_request = {
            "version": self._version,
            "from": from_addr,
            "to": score_addr,
            "dataType": "call",
            "data": {"method": func_name, "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, value * ICX_IN_LOOP)

    def _create_deploy_score_tx_with_timestamp(
        self, timestamp: int, value: int
    ) -> dict:
        return self.create_deploy_score_tx(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
            timestamp_us=timestamp,
            deploy_params={"value": hex(value * ICX_IN_LOOP)},
        )

    def _create_invalid_deploy_tx(
        self,
        from_: Union["EOAAccount", "Address", None],
        to_: Union["EOAAccount", "Address"],
        content: Any = None,
    ):
        addr_from: Optional["Address"] = self._convert_address_from_address_type(from_)
        addr_to: "Address" = self._convert_address_from_address_type(to_)

        deploy_params: dict = {}
        deploy_data: dict = {
            "contentType": "application/zip",
            "content": content,
            "params": deploy_params,
        }

        timestamp_us: int = create_timestamp()
        nonce: int = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "stepLimit": DEFAULT_DEPLOY_STEP_LIMIT,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "deploy",
            "data": deploy_data,
        }

        method = "icx_sendTransaction"
        # Insert txHash into request params
        request_params["txHash"] = create_tx_hash()
        tx = {"method": method, "params": request_params}

        return tx

    def _deploy_score(
        self,
        score_name: str,
        value: int,
        expected_status: bool = True,
        to_: Optional["Address"] = SYSTEM_SCORE_ADDRESS,
        data: bytes = None,
    ) -> List["TransactionResult"]:
        return self.deploy_score(
            score_root="sample_deploy_scores",
            score_name=score_name,
            from_=self._accounts[0],
            deploy_params={"value": hex(value * ICX_IN_LOOP)},
            expected_status=expected_status,
            to_=to_,
            data=data,
        )

    def test_score(self):
        # 1. deploy
        value1 = 1
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        score_addr1: "Address" = tx_results[0].score_address

        # 2. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 3. set value: value2
        value2 = 2
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr1,
            func_name="set_value",
            params={"value": hex(value2 * ICX_IN_LOOP)},
        )

        # 4. assert get value: 2 * value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

        expect_ret = {}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_score_update_governance(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
        )
        tx_hash1: bytes = tx_results[0].tx_hash
        score_addr1: "Address" = tx_results[0].score_address

        # 2. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 3. set value: value2
        value2 = 2 * ICX_IN_LOOP
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr1,
            func_name="set_value",
            params={"value": hex(value2 * ICX_IN_LOOP)},
        )

        # 4. assert get value: 2 * value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

        expect_ret = {"current": {"status": "active", "deployTxHash": tx_hash1}}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_fake_system_score(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_fake_system_score")
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/fake_system_score",
            from_=self._admin,
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
            expected_status=False,
        )
        raise_exception_end_tag("test_fake_system_score")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertIn(f"Not a system SCORE", tx_results[0].failure.message)

    def test_fake_system_score_wrong_owner(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_fake_system_score_wrong_owner")
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/fake_system_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(value1 * ICX_IN_LOOP)},
            expected_status=False,
        )
        raise_exception_end_tag("test_fake_system_score_wrong_owner")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertIn(f"Not a system SCORE", tx_results[0].failure.message)

    def test_score_address_already_in_use(self):
        self.update_governance()

        # 1. deploy
        timestamp = 1
        value1 = 1
        tx1: dict = self._create_deploy_score_tx_with_timestamp(
            timestamp=timestamp, value=value1
        )
        tx2: dict = self._create_deploy_score_tx_with_timestamp(
            timestamp=timestamp, value=value1
        )

        raise_exception_start_tag("test_score_address_already_in_use")
        prev_block, hash_list = self.make_and_req_block([tx1, tx2])
        raise_exception_end_tag("test_score_address_already_in_use")

        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1: "Address" = tx_results[0].score_address

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(
            tx_results[1].failure.message,
            f"SCORE address already in use: {str(score_addr1)}",
        )

        # 2. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 3. set value: value2
        value2 = 2
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr1,
            func_name="set_value",
            params={"value": hex(value2 * ICX_IN_LOOP)},
        )

        # 4. assert get value: 2 * value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

    def test_deploy_invalid_content(self):
        self.update_governance()

        # Update revision
        self.set_revision(3)

        # 1. deploy with str content
        tx = self._create_invalid_deploy_tx(
            from_=self._accounts[0], to_=SYSTEM_SCORE_ADDRESS, content="invalid"
        )

        raise_exception_start_tag("test_score_no_zip")
        prev_block, hash_list = self.make_and_req_block([tx])
        raise_exception_end_tag("test_score_no_zip")
        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, f"Invalid content data")

        # 2. deploy with int content
        tx = self._create_invalid_deploy_tx(
            from_=self._accounts[0], to_=SYSTEM_SCORE_ADDRESS, content=1000
        )

        raise_exception_start_tag("test_score_no_zip")
        prev_block, hash_list = self.make_and_req_block([tx])
        raise_exception_end_tag("test_score_no_zip")
        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, f"Invalid content data")

        # 3. deploy content with hex(no prefix)
        tx = self._create_invalid_deploy_tx(
            from_=self._accounts[0], to_=SYSTEM_SCORE_ADDRESS, content="1a2c3b"
        )

        raise_exception_start_tag("test_score_no_zip")
        prev_block, hash_list = self.make_and_req_block([tx])
        raise_exception_end_tag("test_score_no_zip")
        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, f"Invalid content data")

        # 3. deploy content with hex(upper case)
        tx = self._create_invalid_deploy_tx(
            from_=self._accounts[0], to_=SYSTEM_SCORE_ADDRESS, content="0x1A2c3b"
        )

        raise_exception_start_tag("test_score_no_zip")
        prev_block, hash_list = self.make_and_req_block([tx])
        raise_exception_end_tag("test_score_no_zip")
        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, f"Invalid content data")

    def test_score_no_zip(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_score_no_zip")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score",
            value=value1,
            data=b"invalid",
            expected_status=False,
        )
        raise_exception_end_tag("test_score_no_zip")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PACKAGE)
        self.assertEqual(tx_results[0].failure.message, f"Bad zip file.")

    def test_score_no_scorebase(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_score_no_scorebase")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score_no_scorebase",
            value=value1,
            expected_status=False,
        )
        raise_exception_end_tag("test_score_no_scorebase")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(
            tx_results[0].failure.message,
            "'SampleScore' object has no attribute 'owner'",
        )

    def test_score_on_install_error(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_score_on_install_error")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score_on_install_error",
            value=value1,
            expected_status=False,
        )
        raise_exception_end_tag("test_score_on_install_error")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "raise exception!")

    def test_score_no_external_func(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_score_no_external_func")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score_no_external_func",
            value=value1,
            expected_status=False,
        )
        raise_exception_end_tag("test_score_no_external_func")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(
            tx_results[0].failure.message, "There is no external method in the SCORE"
        )

    def test_score_with_korean_comments(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("test_score_with_korean_comments")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score_with_korean_comments",
            value=value1,
            expected_status=False,
        )
        raise_exception_end_tag("test_score_with_korean_comments")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

    def test_score_no_python(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        raise_exception_start_tag("sample_deploy_scores")
        tx_results: List["TransactionResult"] = self._deploy_score(
            score_name="install/sample_score_no_python",
            value=value1,
            expected_status=False,
        )

        raise_exception_end_tag("sample_deploy_scores")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

    def test_score_tbears_mode(self):
        self.update_governance()

        # 1. deploy
        value1 = 1
        tx1 = self.create_deploy_score_tx(
            "sample_deploy_scores",
            "install/sample_score",
            self._accounts[0],
            SYSTEM_SCORE_ADDRESS,
            deploy_params={"value": hex(value1)},
            is_sys=True,
        )

        raise_exception_start_tag("test_score_tbears_mode")
        prev_block, hash_list = self.make_and_req_block([tx1])
        raise_exception_end_tag("test_score_tbears_mode")

        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIsInstance(tx_results[0].failure.message, str)

    def test_duplicated_deploy_tx_legacy(self):
        block_height: int = self._block_height + 1

        # 1. deploy
        value1 = 1
        tx = self.create_deploy_score_tx(
            "sample_deploy_scores",
            "install/sample_score",
            self._accounts[0],
            SYSTEM_SCORE_ADDRESS,
            deploy_params={"value": hex(value1)},
        )

        prev_block, hash_list = self.make_and_req_block([tx], block_height=block_height)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        prev_block, hash_list = self.make_and_req_block([tx], block_height=block_height)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        self._write_precommit_state(prev_block)

    def test_duplicated_deploy_tx(self):
        self.update_governance()

        block_height: int = self._block_height + 1

        # 1. deploy
        value1 = 1
        tx = self.create_deploy_score_tx(
            "sample_deploy_scores",
            "install/sample_score",
            self._accounts[0],
            SYSTEM_SCORE_ADDRESS,
            deploy_params={"value": hex(value1)},
        )

        prev_block, hash_list = self.make_and_req_block([tx], block_height=block_height)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        prev_block, tx_results = self.make_and_req_block(
            [tx], block_height=block_height
        )
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        self._write_precommit_state(prev_block)
