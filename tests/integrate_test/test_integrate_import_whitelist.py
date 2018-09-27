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
from iconservice.icon_constant import ConfigKey
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateImportWhiteList(TestIntegrateBase):
    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: True}}

    def _import_query_request(self, import_stmt: str):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "isInImportWhiteList",
                "params": {
                    "import_stmt": import_stmt,

                }
            }
        }

        return query_request

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
        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addImportWhiteList',
                                       {"import_stmt": "{'json': [],'os': ['path'],'base.exception': "
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
                                       {"import_stmt": "{'json': [],'os': ['path'],"
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
                                       {"import_stmt": "{'base.exception': ['ExceptionCode']}"})
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
        tx1 = self._make_deploy_tx("test_scores",
                                   "l_coin_0_5_0_using_import_os",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        # add import whitelist
        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addImportWhiteList',
                                       {"import_stmt": "{'os': []}"})

        tx3 = self._make_deploy_tx("test_scores",
                                   "l_coin_0_5_0_using_import_os",
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
        deploy_list = [
                       'import/test_score_import_in_top_level',
                       'import/test_score_import_in_method',
                       'import/test_score_import_in_function',
                       'import/test_score_import_in_class',
                       'import/linkcoin_import_in_submodule',
                       'import/linkcoin_import_in_indirect_submodule',
                       'import/linkcoin_import_in_indirect_submodule_method',
                       'import/test_score_exec_top_level',
                       'import/test_score_exec_function',
                       'import/test_score_exec_method',
                       'import/linkcoin_exec_in_submodule',
                       'import/linkcoin_exec_in_indirect_submodule',
                       'import/as/test_score_import_in_top_level',
                       'import/as/test_score_import_in_class',
                       'import/as/test_score_import_in_method',
                       'import/as/test_score_import_in_function',
                       'import/as/linkcoin_import_in_submodule',
                       'import/as/linkcoin_import_in_indirect_submodule',
                       'import/as/linkcoin_import_in_indirect_submodule_method']

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