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

import unittest

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey, IconServiceFlag
from tests import raise_exception_start_tag, raise_exception_end_tag, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateImportWhiteList(TestIntegrateBase):
    def _import_query_request(self, importStmt: str):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "isInImportWhiteList",
                "params": {
                    "importStmt": importStmt,

                }
            }
        }

        return query_request

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def import_white_list_enable(self):
        tx1 = self._make_deploy_tx("test_builtin",
                                   "latest_version/governance",
                                   self._admin,
                                   GOVERNANCE_SCORE_ADDRESS)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'updateServiceConfig',
                                       {"serviceFlag": hex(IconServiceFlag.SCORE_PACKAGE_VALIDATOR)})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

    def test_governance_call_about_add_remove_import_white_list_no_owner(self):
        self.import_white_list_enable()

        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addImportWhiteList',
                                        {"importStmt": "{ 'json': [] }"})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid sender: not owner")

        tx_result = self._external_call(self._addr_array[0],
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeImportWhiteList',
                                        {"importStmt": "{ 'json': [] }"})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid sender: not owner")

    def test_governance_call_about_add_remove_import_white_list_invalid_params(self):
        self.import_white_list_enable()

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'addImportWhiteList',
                                        {"importStmt": ""})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message,
                         "Invalid import statement: Expecting value: line 1 column 1 (char 0)")

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'removeImportWhiteList',
                                        {"importStmt": ""})
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message,
                         "Invalid import statement: Expecting value: line 1 column 1 (char 0)")

    def test_score_import_white_list(self):
        self.import_white_list_enable()

        # query import whitelist
        query_request = self._import_query_request("{ 'iconservice': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist
        query_request = self._import_query_request("{ 'json': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # add import whitelist
        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addImportWhiteList',
                                       {"importStmt": "{'json': [],'os': ['path'],'base.exception': "
                                                       "['ExceptionCode','RevertException']}"})
        prev_block, tx_results = self._make_and_req_block([tx1])

        # confirm block
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # query import whitelist
        query_request = self._import_query_request("{'json': [],'os': ['path'],'base.exception': "
                                                   "['ExceptionCode','RevertException']}")
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
        query_request = self._import_query_request("{ 'base.exception': ['RevertException'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': ['RevertException', 'ExceptionCode'] }"
        query_request = self._import_query_request("{ 'base.exception': ['RevertException', 'ExceptionCode'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': [] }"
        query_request = self._import_query_request("{ 'base.exception': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # remove import whitelist
        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'removeImportWhiteList',
                                       {"importStmt": "{'json': [],'os': ['path'],"
                                                       "'base.exception': ['RevertException']}"})
        prev_block, tx_results = self._make_and_req_block([tx1])

        # confirm block
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

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
        query_request = self._import_query_request("{ 'base.exception': ['RevertException'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist "{ 'base.exception': ['ExceptionCode'] }"
        query_request = self._import_query_request("{ 'base.exception': ['ExceptionCode'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

        # query import whitelist "{ 'base.exception': [] }"
        query_request = self._import_query_request("{ 'base.exception': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # remove import whitelist
        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'removeImportWhiteList',
                                       {"importStmt": "{'base.exception': ['ExceptionCode']}"})
        prev_block, tx_results = self._make_and_req_block([tx1])

        # confirm block
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # query import whitelist "{ 'base.exception': ['ExceptionCode'] }"
        query_request = self._import_query_request("{ 'base.exception': ['ExceptionCode'] }")
        response = self._query(query_request)
        self.assertEqual(response, int(False))

        # query import whitelist
        query_request = self._import_query_request("{ 'iconservice': [] }")
        response = self._query(query_request)
        self.assertEqual(response, int(True))

    def test_apply_score_import_white_list(self):
        self.import_white_list_enable()

        tx1 = self._make_deploy_tx("test_scores",
                                   "test_score_using_import_os",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        # add import whitelist
        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addImportWhiteList',
                                       {"importStmt": "{'os': []}"})

        tx3 = self._make_deploy_tx("test_scores",
                                   "test_score_using_import_os",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        raise_exception_start_tag("test_apply_score_import_white_list")
        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])
        raise_exception_end_tag("test_apply_score_import_white_list")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))

    def test_deploy_invalid_score(self):
        self.import_white_list_enable()

        deploy_list = [
            'import_test/test_score_import_in_top_level',
            'import_test/test_score_import_in_method',
            'import_test/test_score_import_in_function',
            'import_test/test_score_import_in_class',
            'import_test/linkcoin_import_in_submodule',
            'import_test/linkcoin_import_in_indirect_submodule',
            'import_test/linkcoin_import_in_indirect_submodule_method',
            'import_test/test_score_exec_top_level',
            'import_test/test_score_exec_function',
            'import_test/test_score_exec_method',
            'import_test/test_score_eval_function',
            'import_test/test_score_eval_method',
            'import_test/test_score_compile_function',
            'import_test/test_score_compile_method',
            'import_test/linkcoin_exec_in_submodule',
            'import_test/linkcoin_exec_in_indirect_submodule',
            'import_test/as_test/test_score_import_in_top_level',
            'import_test/as_test/test_score_import_in_class',
            'import_test/as_test/test_score_import_in_method',
            'import_test/as_test/test_score_import_in_function',
            'import_test/as_test/linkcoin_import_in_submodule',
            'import_test/as_test/linkcoin_import_in_indirect_submodule',
            'import_test/as_test/linkcoin_import_in_indirect_submodule_method'
        ]

        tx_list = [self._make_deploy_tx('test_deploy_scores', deploy_name,
                                        self._addr_array[0], ZERO_SCORE_ADDRESS)
                   for deploy_name in deploy_list]

        raise_exception_start_tag("test_deploy_invalid_score")
        prev_block, tx_results = self._make_and_req_block(tx_list)
        raise_exception_end_tag("test_deploy_invalid_score")

        self._write_precommit_state(prev_block)

        for tx_result in tx_results:
            self.assertEqual(tx_result.status, int(False))


if __name__ == '__main__':
    unittest.main()
