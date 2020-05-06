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

"""governance SCORE testcase
"""

from typing import TYPE_CHECKING, List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IconServiceFlag
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateImportWhiteList(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.init()

    def init(self):
        tx1: dict = self.create_deploy_score_tx(
            score_root="sample_builtin",
            score_name="latest_version/governance",
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
        )
        tx2: dict = self.create_score_call_tx(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="updateServiceConfig",
            params={"serviceFlag": hex(IconServiceFlag.SCORE_PACKAGE_VALIDATOR)},
        )
        self.process_confirm_block_tx([tx1, tx2])

    def _import_query_request(self, import_stmt: str):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "isInImportWhiteList",
                "params": {"importStmt": import_stmt,},
            },
        }

        return query_request

    def test_governance_call_about_add_remove_import_white_list_no_owner(self):
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": "{ 'json': [] }"},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid sender: not owner")

        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeImportWhiteList",
            params={"importStmt": "{ 'json': [] }"},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid sender: not owner")

    def test_governance_call_about_add_remove_import_white_list_invalid_params(self):
        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": ""},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message,
            "Invalid import statement: Expecting value: line 1 column 1 (char 0)",
        )

        tx_results: List["TransactionResult"] = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeImportWhiteList",
            params={"importStmt": ""},
            expected_status=False,
        )
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(
            tx_results[0].failure.message,
            "Invalid import statement: Expecting value: line 1 column 1 (char 0)",
        )

    def test_score_import_white_list(self):
        # query import whitelist
        query_request = self._import_query_request("{ 'iconservice': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist
        query_request = self._import_query_request("{ 'json': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # add import whitelist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={
                "importStmt": "{'json': [],'os': ['path'],'base.exception': ['ExceptionCode','RevertException']}"
            },
        )

        # query import whitelist
        query_request = self._import_query_request(
            "{'json': [],'os': ['path'],'base.exception': "
            "['ExceptionCode','RevertException']}"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'json': [] }"
        query_request = self._import_query_request("{ 'json': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'json': ['loads'] }"
        query_request = self._import_query_request("{ 'json': ['loads'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'os': ['path'] }"
        query_request = self._import_query_request("{ 'os': ['path'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'os': [] }"
        query_request = self._import_query_request("{ 'os': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'base.exception': ['RevertException'] }"
        query_request = self._import_query_request(
            "{ 'base.exception': ['RevertException'] }"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': ['RevertException', 'ExceptionCode'] }"
        query_request = self._import_query_request(
            "{ 'base.exception': ['RevertException', 'ExceptionCode'] }"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': [] }"
        query_request = self._import_query_request("{ 'base.exception': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # remove import whitelist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeImportWhiteList",
            params={
                "importStmt": "{'json': [],'os': ['path'],'base.exception': ['RevertException']}"
            },
        )

        # query import whitelist "{ 'json': [] }"
        query_request = self._import_query_request("{ 'json': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'json': ['loads'] }"
        query_request = self._import_query_request("{ 'json': ['loads'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'os': ['path'] }"
        query_request = self._import_query_request("{ 'os': ['path'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'os': [] }"
        query_request = self._import_query_request("{ 'os': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'base.exception': ['RevertException'] }"
        query_request = self._import_query_request(
            "{ 'base.exception': ['RevertException'] }"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'base.exception': ['ExceptionCode'] }"
        query_request = self._import_query_request(
            "{ 'base.exception': ['ExceptionCode'] }"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': [] }"
        query_request = self._import_query_request("{ 'base.exception': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # remove import whitelist
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeImportWhiteList",
            params={"importStmt": "{'base.exception': ['ExceptionCode']}"},
        )

        # query import whitelist "{ 'base.exception': ['ExceptionCode'] }"
        query_request = self._import_query_request(
            "{ 'base.exception': ['ExceptionCode'] }"
        )
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist
        query_request = self._import_query_request("{ 'iconservice': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

    def test_apply_score_import_white_list(self):
        tx1: dict = self.create_deploy_score_tx(
            score_root="sample_scores",
            score_name="sample_score_using_import_os",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
        )
        tx2: dict = self.create_score_call_tx(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": "{'os': []}"},
        )
        tx3: dict = self.create_deploy_score_tx(
            score_root="sample_scores",
            score_name="sample_score_using_import_os",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
        )

        raise_exception_start_tag("sample_apply_score_import_white_list")
        prev_block, hash_list = self.make_and_req_block([tx1, tx2, tx3])
        raise_exception_end_tag("sample_apply_score_import_white_list")

        self._write_precommit_state(prev_block)
        tx_results: List["TransactionResult"] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))

    def test_apply_score_multiply_import(self):
        # add import whitelist
        tx1: dict = self.create_score_call_tx(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": "{'struct': ['pack', 'unpack']}"},
        )

        tx2: dict = self.create_deploy_score_tx(
            score_root="sample_deploy_scores",
            score_name="import_test/import_multiply",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
        )

        self.process_confirm_block_tx([tx1, tx2])

    def test_normal(self):
        tx1: dict = self.create_score_call_tx(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": "{'os': ['path']}"},
        )

        tx2: dict = self.create_deploy_score_tx(
            score_root="sample_deploy_scores",
            score_name="import_test/import_normal",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
        )

        self.process_confirm_block_tx([tx1, tx2])

    def test_deploy_invalid_score(self):

        deploy_list = [
            "import_test/sample_score_import_in_top_level",
            "import_test/sample_score_import_in_method",
            "import_test/sample_score_import_in_function",
            "import_test/sample_score_import_in_class",
            "import_test/import_in_submodule",
            "import_test/import_in_indirect_submodule",
            "import_test/import_in_indirect_submodule_method",
            "import_test/sample_score_exec_top_level",
            "import_test/sample_score_exec_function",
            "import_test/sample_score_exec_method",
            "import_test/sample_score_eval_function",
            "import_test/sample_score_eval_method",
            "import_test/sample_score_compile_function",
            "import_test/sample_score_compile_method",
            "import_test/exec_in_submodule",
            "import_test/exec_in_indirect_submodule",
            "import_test/as_test/sample_score_import_in_top_level",
            "import_test/as_test/sample_score_import_in_class",
            "import_test/as_test/sample_score_import_in_method",
            "import_test/as_test/sample_score_import_in_function",
            "import_test/as_test/sample_in_submodule",
            "import_test/as_test/sample_in_indirect_submodule",
            "import_test/as_test/sample_in_indirect_submodule_method",
            "import_test/import_builtin",
            "import_test/import_builtin2",
            "import_test/import_builtin3",
            "import_test/import_package",
        ]

        tx_list = [
            self.create_deploy_score_tx(
                score_root="sample_deploy_scores",
                score_name=deploy_name,
                from_=self._accounts[0],
                to_=SYSTEM_SCORE_ADDRESS,
            )
            for deploy_name in deploy_list
        ]

        raise_exception_start_tag("sample_deploy_invalid_score")
        self.process_confirm_block_tx(tx_list, expected_status=False)
        self.make_and_req_block(tx_list)
        raise_exception_end_tag("sample_deploy_invalid_score")
