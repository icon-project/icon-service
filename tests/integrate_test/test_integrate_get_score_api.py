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

from iconservice.base.address import ZERO_SCORE_ADDRESS
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateGetScoreApi(TestIntegrateBase):

    def test_get_score_api(self):
        tx1 = self._make_deploy_tx("get_api",
                                   "get_api1",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        tx2 = self._make_deploy_tx("get_api",
                                   "get_api2",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        score_addr2 = tx_results[1].score_address

        query_request = {
            "address": score_addr1
        }
        response1 = self._query(query_request, 'icx_getScoreApi')

        query_request = {
            "address": score_addr2
        }
        response2 = self._query(query_request, 'icx_getScoreApi')

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
                'readonly': True
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'payable': True
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
                'readonly': True
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
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
                'readonly': True
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'payable': True
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
                'readonly': True
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
                'readonly': True
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
            }
        ]
        self.assertEqual(response2, expect_value2)

    def test_get_score_api_update(self):
        tx1 = self._make_deploy_tx("get_api",
                                   "get_api1",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        tx2 = self._make_deploy_tx("get_api",
                                   "get_api2",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        score_addr2 = tx_results[1].score_address

        tx3 = self._make_deploy_tx("get_api",
                                   "get_api1_update",
                                   self._addr_array[0],
                                   score_addr1)

        tx4 = self._make_deploy_tx("get_api",
                                   "get_api2_update",
                                   self._addr_array[0],
                                   score_addr2)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

        query_request = {
            "address": score_addr1
        }
        response1 = self._query(query_request, 'icx_getScoreApi')

        query_request = {
            "address": score_addr2
        }
        response2 = self._query(query_request, 'icx_getScoreApi')

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
                'readonly': True
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
                'readonly': True
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'payable': True
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
                'readonly': True
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
                'readonly': True
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
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
                'readonly': True
            },
            {
                'type': 'fallback',
                'name': 'fallback',
                'payable': True
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
                'readonly': True
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
                'readonly': True
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
            }
        ]
        self.assertEqual(response2, expect_value2)

    def test_get_score_no_fallback(self):
        tx1 = self._make_deploy_tx("get_api",
                                   "get_api3",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "address": score_addr1
        }
        response1 = self._query(query_request, 'icx_getScoreApi')

        expect_value1 = [
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
                'readonly': True
            },
            {
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
            }
        ]
        self.assertEqual(response1, expect_value1)

        tx2 = self._make_deploy_tx("get_api",
                                   "get_api4",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        raise_exception_start_tag("test_get_score_no_fallback")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_get_score_no_fallback")
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))


if __name__ == '__main__':
    unittest.main()
