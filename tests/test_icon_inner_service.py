# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

import asyncio
import os
import time
import unittest
from typing import TYPE_CHECKING

from iconcommons.icon_config import IconConfig
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, \
    GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import DATA_BYTE_ORDER, IconDeployFlag, ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_block_hash, create_address, create_tx_hash, rmtree
from tests.in_memory_zip import InMemoryZip

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestInnerServiceEngine(unittest.TestCase):
    asnyc_loop_array = []

    def setUp(self):
        self._state_db_root_path = '.statedb'
        self._score_root_path = '.score'

        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        self._admin_addr = create_address(AddressPrefix.EOA, b'ADMIN')
        conf = IconConfig("", default_icon_config)
        conf.load({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)
        self._inner_task._open()

        self._genesis_addr = create_address(AddressPrefix.EOA, b'genesis')
        self._addr1 = create_address(AddressPrefix.EOA, b'addr1')

        self._genesis_block_hash, is_commit, tx_results = self._run_async(self._genesis_invoke(0))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def tearDown(self):
        self._inner_task._close()
        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        for loop in self.asnyc_loop_array:
            loop.close()
        self.asnyc_loop_array.clear()

    @classmethod
    def _run_async(cls, asnyc_func):
        loop = asyncio.new_event_loop()
        cls.asnyc_loop_array.append(loop)
        asyncio.get_event_loop().is_closed()
        return loop.run_until_complete(asnyc_func)

    async def _genesis_invoke(self, block_index: int = 0) -> tuple:
        tx_hash = create_tx_hash(b'genesis')
        tx_timestamp_us = int(time.time() * 10 ** 6)
        version = 3
        request_params = {
            'txHash': bytes.hex(tx_hash),
            'version': hex(version),
            'timestamp': hex(tx_timestamp_us)
        }

        tx = {
            'method': 'icx_sendTransaction',
            'params': request_params,
            'genesisData': {
                "accounts": [
                    {
                        "name": "genesis",
                        "address": str(self._genesis_addr),
                        "balance": hex(100 * 10 ** 18)
                    },
                    {
                        "name": "fee_treasury",
                        "address": "hx1000000000000000000000000000000000000000",
                        "balance": hex(0)
                    }
                ]
            },
        }

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = tx_timestamp_us
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, DATA_BYTE_ORDER))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us)
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _send_icx_invoke(self,
                               addr_from: 'Address',
                               addr_to: 'Address',
                               value: int,
                               block_index: int,
                               prev_block_hash: str):

        version = 3
        step_limit = 5000000
        tx_timestamp_us = int(time.time() * 10 ** 6)
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(addr_to),
            "value": hex(value),
            "stepLimit": hex(step_limit),
            "timestamp": hex(tx_timestamp_us),
            "nonce": hex(nonce),
            "signature": signature
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash(b'txHash1')
        request_params['txHash'] = bytes.hex(tx_hash)
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)
        self.assertEqual(response, hex(0))

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, DATA_BYTE_ORDER))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _install_sample_token_invoke(self, score_name: str, to_addr: 'Address', block_index: int,
                                           prev_block_hash: str):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'tests/sample/{score_name}')
        install_data = {'contentType': 'application/tbears', 'content': path}

        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'addr1')
        step_limit = 5000000
        tx_timestamp_us = int(time.time() * 10 ** 6)
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(from_addr),
            "to": str(to_addr),
            "stepLimit": hex(step_limit),
            "timestamp": hex(tx_timestamp_us),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "deploy",
            "data": install_data
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash(block_index.to_bytes(1, 'big'))
        request_params['txHash'] = bytes.hex(tx_hash)
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = tx_timestamp_us
        block_hash = create_block_hash(block_index.to_bytes(1, 'big'))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _install_sample_token_invoke_zip(self, zip_name: str, to_addr: 'Address', block_index: int,
                                           prev_block_hash: str):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'tests/sample/{zip_name}')
        mz = InMemoryZip()
        mz.zip_in_memory(path)
        data = f'0x{mz.data.hex()}'

        install_data = {'contentType': 'application/zip', 'content': data}

        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'addr1')
        step_limit = 5000000
        tx_timestamp_us = int(time.time() * 10 ** 6)
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(from_addr),
            "to": str(to_addr),
            "stepLimit": hex(step_limit),
            "timestamp": hex(tx_timestamp_us),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "deploy",
            "data": install_data
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash(block_index.to_bytes(1, 'big'))
        request_params['txHash'] = bytes.hex(tx_hash)
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_index.to_bytes(1, 'big'))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _accept_deploy_score(self,
                                   block_index: int,
                                   prev_block_hash: str,
                                   addr_from: 'Address',
                                   accept_tx_hash: str):
        version = 3
        step_limit = 5000000
        timestamp = 12345
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "value": hex(0),
            "stepLimit": hex(step_limit),
            "timestamp": hex(timestamp),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "call",
            "data": {
                "method": "acceptScore",
                "params": {
                    "txHash": accept_tx_hash
                }
            }
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash()
        request_params['txHash'] = bytes.hex(tx_hash)
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)
        self.assertEqual(response, hex(0))

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, DATA_BYTE_ORDER))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _update_governance_invoke(self, block_index: int, prev_block_hash: str):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'iconservice/builtin_scores/governance')
        install_data = {'contentType': 'application/tbears', 'content': path}

        version = 3
        from_addr = self._admin_addr
        to_addr = GOVERNANCE_SCORE_ADDRESS
        step_limit = 5000000
        timestamp = 12345
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(from_addr),
            "to": str(to_addr),
            "stepLimit": hex(step_limit),
            "timestamp": hex(timestamp),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "deploy",
            "data": install_data
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash()
        request_params['txHash'] = bytes.hex(tx_hash)
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, DATA_BYTE_ORDER))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        is_commit = False
        if not isinstance(tx_results, dict):
            await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_results[bytes.hex(tx_hash)]['status'] == hex(1):
            is_commit = True
            await self._inner_task.write_precommit_state(precommit_request)
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return bytes.hex(block_hash), is_commit, invoke_response
        else:
            return bytes.hex(block_hash), is_commit, list(tx_results.values())

    async def _icx_call(self, request: dict):
        method = 'icx_call'
        make_request = {'method': method, 'params': request}

        response = await self._inner_task.query(make_request)
        return response

    async def _icx_get_score_api(self, request: dict):
        method = 'icx_getScoreApi'
        make_request = {'method': method, 'params': request}

        response = await self._inner_task.query(make_request)
        return response

    def test_invoke_success(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 2, prev_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_invoke_fail1(self):
        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, self._genesis_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)

    def test_invoke_fail2(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 3, prev_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)

    def test_invoke_fail3(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, prev_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)

    def test_invoke_fail4(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 2, ""))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)

    def test_install_sample_token(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'sample_token', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_query_method_sample_token(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'sample_token', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        version = 3
        token_addr = tx_results[0]['scoreAddress']
        addr_from = create_address(AddressPrefix.EOA, b'addr1')

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": token_addr,
            "dataType": "call",
            "data": {
                "method": "total_supply",
                "params": {}
            }
        }
        response = self._run_async(self._icx_call(request))
        self.assertEqual(response, "0x3635c9adc5dea00000")

    def test_governance_score1(self):
        self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
            IconDeployFlag.ENABLE_DEPLOY_AUDIT

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'sample_token', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        version = 3
        token_addr = tx_results[0]['scoreAddress']
        addr_from = create_address(AddressPrefix.EOA, b'addr1')

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": str(token_addr)
                }
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual('pending', response['next']['status'])

    def test_governance_score2(self):
        self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
            IconDeployFlag.ENABLE_DEPLOY_AUDIT

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'install1', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        next_tx_hash = tx_results[0]['txHash']

        version = 3
        token_addr = tx_results[0]['scoreAddress']
        addr_from = create_address(AddressPrefix.EOA, b'addr1')

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": str(token_addr)
                }
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual('pending', response['next']['status'])
        self.assertEqual(next_tx_hash, response['next']['deployTxHash'][2:])

        prev_block_hash, is_commit, tx_results = self._run_async(self._accept_deploy_score(
            2, prev_block_hash, self._admin_addr, next_tx_hash))

        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))
        audit_tx_hash = tx_results[0]['txHash']

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": token_addr
                }
            }
        }
        response = self._run_async(self._icx_call(request))
        self.assertEqual('active', response['current']['status'])
        self.assertEqual(audit_tx_hash, response['current']['auditTxHash'][2:])

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": token_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
                "params": {}
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual(response, "Hello")

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke('install2', token_addr, 3, prev_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))
        current_tx_hash = next_tx_hash
        next_tx_hash = tx_results[0]['txHash']

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": token_addr
                }
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual('active', response['current']['status'])
        self.assertEqual(current_tx_hash, response['current']['deployTxHash'][2:])
        self.assertEqual(audit_tx_hash, response['current']['auditTxHash'][2:])
        self.assertEqual('pending', response['next']['status'])
        self.assertEqual(next_tx_hash, response['next']['deployTxHash'][2:])

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._accept_deploy_score(4, prev_block_hash, self._admin_addr, next_tx_hash))

        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))
        audit_tx_hash = tx_results[0]['txHash']

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": token_addr
                }
            }
        }

        response = self._run_async(self._icx_call(request))
        current_tx_hash = next_tx_hash
        self.assertEqual('active', response['current']['status'])
        self.assertEqual(current_tx_hash, response['current']['deployTxHash'][2:])
        self.assertEqual(audit_tx_hash, response['current']['auditTxHash'][2:])

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": token_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
                "params": {}
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual(response, "Hello2")

    def test_update_score(self):
        self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
            IconDeployFlag.NONE

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'install1', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        version = 3
        token_addr = tx_results[0]['scoreAddress']

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'install2', token_addr, 2, prev_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        request = {
            "version": hex(version),
            "from": str(self._admin_addr),
            "to": token_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
                "params": {}
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual(response, "Hello2")

    def test_get_score_api(self):
        self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
            IconDeployFlag.NONE

        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke(
                'sample_token', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        version = 3
        token_addr = tx_results[0]['scoreAddress']

        request = {
            "version": hex(version),
            "address": token_addr
        }

        response = self._run_async(self._icx_get_score_api(request))
        self.assertTrue(isinstance(response, list))

    def test_update_governance(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._update_governance_invoke(1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_duplicate_score_install(self):
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke_zip(
                'install1', ZERO_SCORE_ADDRESS, 1, self._genesis_block_hash))
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._install_sample_token_invoke_zip(
                'install2', ZERO_SCORE_ADDRESS, 2, prev_block_hash))

        version = 3
        token_addr = tx_results[0]['scoreAddress']
        addr_from = create_address(AddressPrefix.EOA, b'addr1')

        request = {
            "version": hex(version),
            "from": str(addr_from),
            "to": token_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
                "params": {}
            }
        }

        response = self._run_async(self._icx_call(request))
        self.assertEqual(response, "Hello2")


if __name__ == '__main__':
    unittest.main()
