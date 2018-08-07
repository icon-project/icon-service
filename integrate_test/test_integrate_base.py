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
import unittest
from typing import Union

import time

from iconservice.base.address import Address, AddressPrefix

from tests import create_block_hash, create_address, create_tx_hash, rmtree
from tests.in_memory_zip import InMemoryZip


class TestIntegrateBase(unittest.TestCase):
    asnyc_loop_array = []

    def setUp(self):
        self._state_db_root_path = '.statedb'
        self._score_root_path = '.score'

        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        self._block_height = 0
        self._prev_block_hash = None
        self._version = 3
        self._step_limit = 4 * 10 ** 6
        self._icx_factor = 10 ** 18

        self._admin_addr = create_address(AddressPrefix.EOA)
        self._genesis_addr = create_address(AddressPrefix.EOA)

        self._inner_task = None

    def tearDown(self):
        if self._inner_task:
            self._inner_task._close()
        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        for loop in self.asnyc_loop_array:
            loop.close()
            self.asnyc_loop_array.clear()

    def _run_async(self, async_func):
        loop = asyncio.new_event_loop()
        self.asnyc_loop_array.append(loop)
        return loop.run_until_complete(async_func)

    async def _genesis_invoke(self) -> tuple:
        tx_hash = create_tx_hash()
        timestamp_us = int(time.time() * 10 ** 6)
        version = 3
        request_params = {
            'txHash': bytes.hex(tx_hash),
            'version': hex(version),
            'timestamp': hex(timestamp_us)
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
        block_height: int = 0
        block_hash = create_block_hash()

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(timestamp_us)
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
            self._block_height += 1
            self._prev_block_hash = block_hash
        else:
            await self._inner_task.remove_precommit_state(precommit_request)

        if tx_results is None:
            return is_commit, invoke_response
        else:
            return is_commit, list(tx_results.values())

    async def _make_deploy_tx(self, sample_root: str, sample_name: str, addr_to: Union[str, 'Address'],
                              addr_from: Union[str, 'Address'], deploy_params: dict = None, timestamp_us: int = None,
                              data: bytes = None, is_sys: bool = False):
        if deploy_params is None:
            deploy_params = {}

        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'integrate_test/sample/{sample_root}/{sample_name}')
        if is_sys:
            deploy_data = {'contentType': 'application/tbears', 'content': path, 'params': deploy_params}
        else:
            if data is None:
                mz = InMemoryZip()
                mz.zip_in_memory(path)
                data = f'0x{mz.data.hex()}'
            else:
                data = f'0x{bytes.hex(data)}'
            deploy_data = {'contentType': 'application/zip', 'content': data, 'params': deploy_params}

        if timestamp_us is None:
            timestamp_us = int(time.time() * 10 ** 6)
        nonce = 0
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        if isinstance(addr_to, Address):
            addr_to = str(addr_to)
        if isinstance(addr_from, Address):
            addr_from = str(addr_from)

        request_params = {
            "version": hex(self._version),
            "from": addr_from,
            "to": addr_to,
            "stepLimit": hex(self._step_limit),
            "timestamp": hex(timestamp_us),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "deploy",
            "data": deploy_data
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
        return response, tx

    async def _make_score_call_tx(self,
                                  addr_from: Union[str, 'Address'],
                                  addr_to: Union[str, 'Address'],
                                  method: str,
                                  params: dict):

        timestamp_us = int(time.time() * 10 ** 6)
        nonce = 0
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        if isinstance(addr_to, Address):
            addr_to = str(addr_to)
        if isinstance(addr_from, Address):
            addr_from = str(addr_from)

        request_params = {
            "version": hex(self._version),
            "from": addr_from,
            "to": addr_to,
            "value": hex(0),
            "stepLimit": hex(self._step_limit),
            "timestamp": hex(timestamp_us),
            "nonce": hex(nonce),
            "signature": signature,
            "dataType": "call",
            "data": {
                "method": method,
                "params": params
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
        return response, tx

    async def _make_icx_send_tx(self,
                                addr_from: Union[str, 'Address'],
                                addr_to: Union[str, 'Address'],
                                value: int):

        timestamp_us = int(time.time() * 10 ** 6)
        nonce = 0
        signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        if isinstance(addr_to, Address):
            addr_to = str(addr_to)
        if isinstance(addr_from, Address):
            addr_from = str(addr_from)

        request_params = {
            "version": hex(self._version),
            "from": addr_from,
            "to": addr_to,
            "value": hex(value),
            "stepLimit": hex(self._step_limit),
            "timestamp": hex(timestamp_us),
            "nonce": hex(nonce),
            "signature": signature
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
        return response, tx

    async def _make_and_req_block(self, tx_list: list, block_height: int = None):
        make_request = {'transactions': tx_list}
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = int(time.time() * 10 ** 6)

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': bytes.hex(block_hash),
            'timestamp': hex(timestamp_us),
            'prevBlockHash': bytes.hex(self._prev_block_hash)
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': bytes.hex(block_hash)}

        invoke_response = await self._inner_task.invoke(make_request)
        tx_results = invoke_response.get('txResults')
        if tx_results is None:
            response = invoke_response
        else:
            response = tx_results
        return precommit_request, response

    async def _write_precommit_state(self, precommit_request: dict):
        ret = await self._inner_task.write_precommit_state(precommit_request)
        self._block_height += 1
        self._prev_block_hash = bytes.fromhex(precommit_request['blockHash'])
        return ret

    async def _remove_precommit_state(self, precommit_request: dict):
        return await self._inner_task.remove_precommit_state(precommit_request)

    async def _query(self, request: dict, method: str = 'icx_call'):
        make_request = {'method': method, 'params': request}

        response = await self._inner_task.query(make_request)
        return response

    def _get_tx_result(self, tx_results: dict, tx: dict) -> dict:
        tx_hash = tx['params']['txHash']
        return tx_results[tx_hash]
