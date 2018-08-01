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
from typing import TYPE_CHECKING

import time

from iconcommons.icon_config import IconConfig
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import DATA_BYTE_ORDER, IconDeployFlag, ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_block_hash, create_address, create_tx_hash, rmtree, raise_exception_start_tag, \
    raise_exception_end_tag
from tests.in_memory_zip import InMemoryZip

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateSimpleInvoke(unittest.TestCase):
    asnyc_loop_array = []

    def setUp(self):
        self._state_db_root_path = '.statedb'
        self._score_root_path = '.score'

        rmtree(self._score_root_path)
        rmtree(self._state_db_root_path)

        self._admin_addr = create_address(AddressPrefix.EOA, b'ADMIN')
        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

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
        raise_exception_start_tag()
        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, self._genesis_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)
        raise_exception_end_tag()

    def test_invoke_fail2(self):
        raise_exception_start_tag()
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 3, prev_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)
        raise_exception_end_tag()

    def test_invoke_fail3(self):
        raise_exception_start_tag()
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 0, prev_block_hash))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)
        raise_exception_end_tag()

    def test_invoke_fail4(self):
        raise_exception_start_tag()
        prev_block_hash, is_commit, tx_results = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 1, self._genesis_block_hash))
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

        prev_block_hash, is_commit, response = \
            self._run_async(self._send_icx_invoke(self._genesis_addr, self._addr1, 1, 2, ""))
        self.assertEqual(is_commit, False)
        self.assertEqual(response['error']['code'], 32000)
        raise_exception_end_tag()


if __name__ == '__main__':
    unittest.main()
