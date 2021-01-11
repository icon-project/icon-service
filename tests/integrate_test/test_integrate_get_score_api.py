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

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, Address
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
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
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
            },
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
        ]
        self.assertEqual(response1, expect_value1)

        expect_value2 = [
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
            },
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
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
            },
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
        ]
        self.assertEqual(response1, expect_value1)

        expect_value2 = [
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
            },
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
                'type': 'eventlog',
                'name': 'Changed',
                'inputs': [
                    {
                        'name': 'value',
                        'type': 'int',
                        'indexed': True
                    }
                ]
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
        ]
        self.assertEqual(response1, expect_value1)

        raise_exception_start_tag("test_get_score_no_fallback")
        self.deploy_score(score_root="get_api",
                          score_name="get_api4",
                          from_=self._accounts[0],
                          expected_status=False)
        raise_exception_end_tag("test_get_score_no_fallback")

    def test_get_score_api_with_payable_only(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="get_api", score_name="payable_only", from_=self._accounts[0])

        score_address: 'Address' = tx_results[0].score_address
        api: dict = self.get_score_api(score_address)

        expected = [
            {
                'type': 'fallback',
                'name': 'fallback',
                'payable': True
            },
            {
                'type': 'function',
                'name': 'get_value',
                'inputs': [{'name': 'value', 'type': 'int'}],
                'outputs': [{'type': 'int'}],
                'readonly': True
            },
            {
                'type': 'function',
                'name': 'set_value',
                'inputs': [{'name': 'value', 'type': 'int'}],
                'outputs': [],
                'payable': True,
            },
        ]

        assert api == expected

    def test_get_score_api_for_system_score(self):
        api: dict = self.get_score_api(SYSTEM_SCORE_ADDRESS)

        expected = [
            {
                "type": "function",
                "name": "estimateUnstakeLockPeriod",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "setStake",
                "inputs": [{"name": "value", "type": "int", "default": 0}],
                "outputs": [],
            },
            {
                "type": "function",
                "name": "getStake",
                "inputs": [{"name": "address", "type": "Address"}],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "claimIScore",
                "inputs": [],
                "outputs": [],
            },
            {
                "type": "eventlog",
                "name": "IScoreClaimed",
                "inputs": [
                    {"name": "iscore", "type": "int"},
                    {"name": "icx", "type": "int"},
                ],
            },
            {
                "type": "eventlog",
                "name": "IScoreClaimedV2",
                "inputs": [
                    {"name": "address", "type": "Address", "indexed": True},
                    {"name": "iscore", "type": "int"},
                    {"name": "icx", "type": "int"},
                ],
            },
            {
                "type": "function",
                "name": "queryIScore",
                "inputs": [{"name": "address", "type": "Address"}],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "registerPRep",
                "inputs": [
                    {"name": "name", "type": "str"},
                    {"name": "country", "type": "str"},
                    {"name": "city", "type": "str"},
                    {"name": "email", "type": "str"},
                    {"name": "website", "type": "str"},
                    {"name": "details", "type": "str"},
                    {"name": "p2pEndpoint", "type": "str"},
                    {"name": "nodeAddress", "type": "Address", "default": None},
                ],
                "outputs": [],
                "payable": True,
            },
            {
                "type": "eventlog",
                "name": "PRepRegistered",
                "inputs": [{"name": "address", "type": "Address"}]
            },
            {
                "type": "function",
                "name": "unregisterPRep",
                "inputs": [],
                "outputs": [],
            },
            {
                "type": "eventlog",
                "name": "PRepUnregistered",
                "inputs": [{"name": "address", "type": "Address"}]
            },
            {
                "type": "function",
                "name": "setPRep",
                "inputs": [
                    {"name": "name", "type": "str", "default": None},
                    {"name": "country", "type": "str", "default": None},
                    {"name": "city", "type": "str", "default": None},
                    {"name": "email", "type": "str", "default": None},
                    {"name": "website", "type": "str", "default": None},
                    {"name": "details", "type": "str", "default": None},
                    {"name": "p2pEndpoint", "type": "str", "default": None},
                    {"name": "nodeAddress", "type": "Address", "default": None},
                ],
                "outputs": [],
            },
            {
                "type": "eventlog",
                "name": "PRepSet",
                "inputs": [{"name": "address", "type": "Address"}]
            },
            {
                "type": "function",
                "name": "setGovernanceVariables",
                "inputs": [{"name": "irep", "type": "int"}],
                "outputs": [],
            },
            {
                "type": "function",
                "name": "getPRep",
                "inputs": [{"name": "address", "type": "Address"}],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getPReps",
                "inputs": [
                    {"name": "startRanking", "type": "int", "default": None},
                    {"name": "endRanking", "type": "int", "default": None},
                ],
                "outputs": [{"type": "list"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getDelegation",
                "inputs": [{"name": "address", "type": "Address"}],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "setDelegation",
                "inputs": [
                    {
                        "name": "delegations",
                        "type": "[]struct",
                        "fields": [
                            {"name": "address", "type": "Address"},
                            {"name": "value", "type": "int"},
                        ],
                        "default": None,
                    }
                ],
                "outputs": []
            },
            {
                "type": "function",
                "name": "getIISSInfo",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getPRepTerm",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getMainPReps",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getSubPReps",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getInactivePReps",
                "inputs": [],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "getScoreDepositInfo",
                "inputs": [{"name": "address", "type": "Address"}],
                "outputs": [{"type": "dict"}],
                "readonly": True,
            },
            {
                "type": "function",
                "name": "burn",
                "inputs": [],
                "outputs": [],
                "payable": True,
            },
            {
                "type": "eventlog",
                "name": "ICXBurnedV2",
                "inputs": [
                    {"name": "address", "type": "Address", "indexed": True},
                    {"name": "amount", "type": "int"},
                    {"name": "totalSupply", "type": "int"},
                ]
            },
        ]

        expected.sort(key=lambda x: x["name"])

        assert api == expected
