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

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateGetScoreApi(TestIntegrateBase):

    def test_get_score_api(self):
        tx1: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api1",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api2",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        response1: dict = self.get_score_api(score_addr1)
        response2: dict = self.get_score_api(score_addr2)

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
        tx1: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api1",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api2",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx1: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api1_update",
                                                from_=self._accounts[0],
                                                to_=score_addr1)
        tx2: dict = self.create_deploy_score_tx(score_root="get_api",
                                                score_name="get_api2_update",
                                                from_=self._accounts[0],
                                                to_=score_addr2)

        self.process_confirm_block_tx([tx1, tx2])
        response1: dict = self.get_score_api(score_addr1)
        response2: dict = self.get_score_api(score_addr2)

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
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="get_api",
                                                                  score_name="get_api3",
                                                                  from_=self._accounts[0])

        score_addr1: 'Address' = tx_results[0].score_address
        response1: dict = self.get_score_api(score_addr1)

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

        raise_exception_start_tag("test_get_score_no_fallback")
        self.deploy_score(score_root="get_api",
                          score_name="get_api4",
                          from_=self._accounts[0],
                          expected_status=False)
        raise_exception_end_tag("test_get_score_no_fallback")
