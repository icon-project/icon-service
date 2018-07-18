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

import shutil
import unittest
import time
import asyncio
import os

from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import DATA_BYTE_ORDER, IconDeployFlag, ConfigKey
from iconservice.icon_config import default_icon_config
from iconcommons.icon_config import IconConfig
from tests import create_block_hash, create_address, create_tx_hash

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIconServiceEngine(unittest.TestCase):
    def setUp(self):
        self._state_db_root_path = '.db'
        self._icon_score_root_path = '.score'

        try:
            shutil.rmtree(self._icon_score_root_path)
            shutil.rmtree(self._state_db_root_path)
        except:
            pass

        self._admin_addr = create_address(AddressPrefix.EOA, b'ADMIN')
        conf = IconConfig("", default_icon_config)
        conf.load({ConfigKey.ADMIN_ADDRESS: str(self._admin_addr)})
        self._inner_task = IconScoreInnerTask(conf)
        self._genesis_addr = create_address(AddressPrefix.EOA, b'genesis')
        self._addr1 = create_address(AddressPrefix.EOA, b'addr1')

    def tearDown(self):
        self._inner_task._close()
        shutil.rmtree(self._icon_score_root_path)
        shutil.rmtree(self._state_db_root_path)

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
        step_limit = 1000
        timestamp = 12345
        nonce = 1
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        request_params = {
            "version": hex(version),
            "from": str(addr_from),
            "to": str(addr_to),
            "value": hex(value),
            "stepLimit": hex(step_limit),
            "timestamp": hex(timestamp),
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

    async def _install_sample_token_invoke(self, score_name: str, to_addr: 'Address', block_index: int, prev_block_hash: str):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'tests/sample/{score_name}')
        install_data = {'contentType': 'application/tbears', 'content': path}

        version = 3
        from_addr = create_address(AddressPrefix.EOA, b'addr1')
        step_limit = 1000
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
        step_limit = 1000
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
        step_limit = 1000
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

    def test_genesis_invoke(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_invoke_success(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 2, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_invoke_fail1(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, prev_block_hash)
            self.assertEqual(is_commit, False)
            self.assertEqual(response['error']['code'], 32000)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_invoke_fail2(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 3, prev_block_hash)
            self.assertEqual(is_commit, False)
            self.assertEqual(response['error']['code'], 32000)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_invoke_fail3(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, prev_block_hash)
            self.assertEqual(is_commit, False)
            self.assertEqual(response['error']['code'], 32000)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_invoke_fail4(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 2, "")
            self.assertEqual(is_commit, False)
            self.assertEqual(response['error']['code'], 32000)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_install_sample_token(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token', ZERO_SCORE_ADDRESS, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_query_method_sample_token(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token', ZERO_SCORE_ADDRESS, 1, prev_block_hash)
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
            response = await self._icx_call(request)
            self.assertEqual(response, "0x3635c9adc5dea00000")

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_governance_score1(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
                IconDeployFlag.ENABLE_DEPLOY_AUDIT

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token', ZERO_SCORE_ADDRESS, 1, prev_block_hash)
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

            response = await self._icx_call(request)
            self.assertEqual('pending', response['next']['status'])

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_governance_score2(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
                IconDeployFlag.ENABLE_DEPLOY_AUDIT

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token', ZERO_SCORE_ADDRESS, 1, prev_block_hash)
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

            response = await self._icx_call(request)
            self.assertEqual('pending', response['next']['status'])
            self.assertEqual(next_tx_hash, response['next']['deployTxHash'][2:])
            prev_block_hash, is_commit, tx_results = \
                await self._accept_deploy_score(2, prev_block_hash, self._admin_addr, next_tx_hash)

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
            response = await self._icx_call(request)
            self.assertEqual('active', response['current']['status'])
            self.assertEqual(audit_tx_hash, response['current']['auditTxHash'][2:])

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

            response = await self._icx_call(request)
            self.assertEqual(response, "0x3635c9adc5dea00000")

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token2', token_addr, 3, prev_block_hash)
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
            response = await self._icx_call(request)
            self.assertEqual('active', response['current']['status'])
            self.assertEqual(current_tx_hash, response['current']['deployTxHash'][2:])
            self.assertEqual(audit_tx_hash, response['current']['auditTxHash'][2:])
            self.assertEqual('pending', response['next']['status'])
            self.assertEqual(next_tx_hash, response['next']['deployTxHash'][2:])

            prev_block_hash, is_commit, tx_results = \
                await self._accept_deploy_score(4, prev_block_hash, self._admin_addr, next_tx_hash)

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

            response = await self._icx_call(request)
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
                    "method": "total_supply",
                    "params": {}
                }
            }

            response = await self._icx_call(request)
            self.assertEqual(response, "0x0")

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_update_score(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            self._inner_task._icon_service_engine._icon_score_deploy_engine._flag = \
                IconDeployFlag.NONE

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token', ZERO_SCORE_ADDRESS, 1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            version = 3
            token_addr = tx_results[0]['scoreAddress']

            prev_block_hash, is_commit, tx_results = \
                await self._install_sample_token_invoke('sample_token2', token_addr, 2, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            request = {
                "version": hex(version),
                "from": str(self._admin_addr),
                "to": token_addr,
                "dataType": "call",
                "data": {
                    "method": "total_supply",
                    "params": {}
                }
            }

            response = await self._icx_call(request)
            self.assertEqual(response, "0x0")

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass

    def test_update_governance(self):
        async def _run():
            prev_block_hash, is_commit, tx_results = await self._genesis_invoke(0)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

            prev_block_hash, is_commit, tx_results = \
                await self._update_governance_invoke(1, prev_block_hash)
            self.assertEqual(is_commit, True)
            self.assertEqual(tx_results[0]['status'], hex(1))

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except RuntimeError:
            pass


if __name__ == '__main__':
    unittest.main()
