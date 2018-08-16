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

from iconcommons.icon_config import IconConfig
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateGetScoreApi(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.sample_root = "get_api"

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_get_score_api(self):
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api1", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response1, hex(0))
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api2", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1, tx2]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']
        tx_result2 = self._get_tx_result(tx_results1, tx2)
        self.assertEqual(tx_result2['status'], hex(True))
        score_addr2 = tx_result2['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        query_request = {
            "address": score_addr1
        }
        response1 = self._run_async(self._query(query_request, 'icx_getScoreApi'))

        query_request = {
            "address": score_addr2
        }
        response2 = self._run_async(self._query(query_request, 'icx_getScoreApi'))

        expect_value1 = [
            {
                'type': 'function',
                'name': 'base_value',
                'inputs': [
                    {
                        'name': 'base_value',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'inputs': [],
                'payable': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value',
                'inputs': [
                    {
                        'name': 'value1',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': '0x1'
                    }
                ]
            }
        ]
        self.assertEqual(response1, expect_value1)

        expect_value2 = [
            {
                'type': 'function',
                'name': 'base_value',
                'inputs': [
                    {
                        'name': 'base_value',
                        'type': 'str'
                    }
                ],
                'outputs': [
                    {
                        'type': 'str'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'inputs': [],
                'payable': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value',
                'inputs': [
                    {
                        'name': 'value2',
                        'type': 'str'
                    }
                ],
                'outputs': [
                    {
                        'type': 'str'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value1',
                'inputs': [],
                'outputs': [
                    {
                        'type': 'str'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': '0x1'
                    }
                ]
            }
        ]
        self.assertEqual(response2, expect_value2)

    def test_get_score_api_update(self):
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api1", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response1, hex(0))
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api2", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1, tx2]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']
        tx_result2 = self._get_tx_result(tx_results1, tx2)
        self.assertEqual(tx_result2['status'], hex(True))
        score_addr2 = tx_result2['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        validate_tx_response3, tx3 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api1_update", score_addr1, self._admin_addr))
        self.assertEqual(validate_tx_response3, hex(0))
        validate_tx_response4, tx4 = self._run_async(
            self._make_deploy_tx(self.sample_root, "get_api2_update", score_addr2, self._admin_addr))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx3, tx4]))

        tx_result3 = self._get_tx_result(tx_results2, tx3)
        self.assertEqual(tx_result3['status'], hex(True))
        tx_result4 = self._get_tx_result(tx_results2, tx4)
        self.assertEqual(tx_result4['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        query_request = {
            "address": score_addr1
        }
        response1 = self._run_async(self._query(query_request, 'icx_getScoreApi'))

        query_request = {
            "address": score_addr2
        }
        response2 = self._run_async(self._query(query_request, 'icx_getScoreApi'))

        expect_value1 = [
            {
                'type': 'function',
                'name': 'base_value1',
                'inputs': [
                    {
                        'name': 'value1',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'function',
                'name': 'base_value2',
                'inputs': [
                    {
                        'name': 'value2',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'inputs': [],
                'payable': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value1',
                'inputs': [
                    {
                        'name': 'value1',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value2',
                'inputs': [
                    {
                        'name': 'value2',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': '0x1'
                    }
                ]
            }
        ]
        self.assertEqual(response1, expect_value1)

        expect_value2 = [
            {
                'type': 'function',
                'name': 'base_value1',
                'inputs': [
                    {
                        'name': 'value1',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'inputs': [],
                'payable': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value',
                'inputs': [
                    {
                        'name': 'value2',
                        'type': 'int'
                    }
                ],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'function',
                'name': 'get_value1',
                'inputs': [],
                'outputs': [
                    {
                        'type': 'int'
                    }
                ],
                'readonly': '0x1'
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': '0x1'
                    }
                ]
            }
        ]
        self.assertEqual(response2, expect_value2)
