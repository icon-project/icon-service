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

from time import sleep
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.base.address import AddressPrefix
from tests import create_block_hash, create_address, create_tx_hash


class TestIconServiceEngine(unittest.TestCase):
    def setUp(self):
        self._state_db_root_path = '.db'
        self._icon_score_root_path = '.score'

        try:
            shutil.rmtree(self._icon_score_root_path)
            shutil.rmtree(self._state_db_root_path)
        except:
            pass

        self._inner_task = IconScoreInnerTask(self._state_db_root_path, self._icon_score_root_path)
        self._genesis_addr = create_address(AddressPrefix.EOA, b'genesis')
        self._addr1 = create_address(AddressPrefix.EOA, b'addr1')

    def tearDown(self):
        async def _run():
            await self._inner_task.close()
            shutil.rmtree(self._icon_score_root_path)
            shutil.rmtree(self._state_db_root_path)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    async def _genesis_invoke(self, block_index: int = 0) -> tuple:
        tx_hash = create_tx_hash(b'genesis')
        tx_timestamp_us = int(time.time() * 10 ** 6)
        request_params = {'txHash': tx_hash, 'timestamp': hex(tx_timestamp_us)}
        tx = {
            'method': '',
            'params': request_params,
            'genesisData': {
                "accounts": [
                    {
                        "name": "genesis",
                        "address": f"{self._genesis_addr}",
                        "balance": "0x2961fff8ca4a62327800000"
                    },
                    {
                        "name": "fee_treasury",
                        "address": "hx1000000000000000000000000000000000000000",
                        "balance": "0x0"
                    }
                ]
            },
        }

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = tx_timestamp_us
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, 'big'))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': block_hash,
            'timestamp': hex(block_timestamp_us)
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': block_hash}

        response = await self._inner_task.invoke(make_request)
        if not isinstance(response, dict):
            response = await self._inner_task.remove_precommit_state(precommit_request)
        elif response[tx_hash]['status'] == hex(1):
            response = await self._inner_task.write_precommit_state(precommit_request)
        else:
            response = await self._inner_task.remove_precommit_state(precommit_request)
        return block_hash, response

    async def _send_icx_invoke(self, addr_from, addr_to, value, block_index: int, prev_block_hash: str):

        request_params = {
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "fee": "0x2386f26fc10000",
            "timestamp": "0x1523327456264040",
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash(b'txHash1')
        request_params['txHash'] = tx_hash
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, 'big'))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': block_hash,
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': block_hash}

        response = await self._inner_task.invoke(make_request)
        is_commit = False
        if not isinstance(response, dict):
            response = await self._inner_task.remove_precommit_state(precommit_request)
        elif response[tx_hash]['status'] == hex(1):
            is_commit = True
            response = await self._inner_task.write_precommit_state(precommit_request)
        else:
            response = await self._inner_task.remove_precommit_state(precommit_request)

        return block_hash, is_commit, response

    async def _install_sample_token_invoke(self, block_index: int, prev_block_hash: str):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        path = os.path.join(root_path, f'tests/sample/sample_token')
        install_data = {'contentType': 'application/tbears', 'content': path}

        request_params = {
            "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "fee": "0x2386f26fc10000",
            "timestamp": "0x1523327456264040",
            "dataType": "install",
            "data": install_data
        }

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        tx_hash = create_tx_hash(b'txHash1')
        request_params['txHash'] = tx_hash
        tx = {
            'method': method,
            'params': request_params
        }

        response = await self._inner_task.validate_transaction(tx)

        make_request = {'transactions': [tx]}
        block_height: int = block_index
        block_timestamp_us = int(time.time() * 10 ** 6)
        block_hash = create_block_hash(block_timestamp_us.to_bytes(8, 'big'))

        make_request['block'] = {
            'blockHeight': hex(block_height),
            'blockHash': block_hash,
            'timestamp': hex(block_timestamp_us),
            'prevBlockHash': prev_block_hash
        }

        precommit_request = {'blockHeight': hex(block_height),
                             'blockHash': block_hash}

        tx_result = await self._inner_task.invoke(make_request)
        is_commit = False
        if not isinstance(tx_result, dict):
            response = await self._inner_task.remove_precommit_state(precommit_request)
        elif tx_result[tx_hash]['status'] == hex(1):
            is_commit = True
            response = await self._inner_task.write_precommit_state(precommit_request)
        else:
            response = await self._inner_task.remove_precommit_state(precommit_request)

        return block_hash, is_commit, list(tx_result.values()), response

    async def _icx_call(self, request: dict):
        method = 'icx_call'
        make_request = {'method': method, 'params': request}

        response = await self._inner_task.query(make_request)
        return response

    def test_genesis_invoke(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_invoke_success(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 2, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_invoke_fail1(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 0, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, False)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_invoke_fail2(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 3, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, False)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_invoke_fail3(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 0, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, False)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_invoke_fail4(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)
            prev_block_hash, is_commit, response = \
                await self._send_icx_invoke(self._genesis_addr, self._addr1, hex(1), 2, "")
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, False)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_install_sample_token(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            self.assertEqual(response, hex(0))
            prev_block_hash, is_commit, tx_result, response = \
                await self._install_sample_token_invoke(1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_run())
        except:
            pass

    def test_query_method_sample_token(self):
        async def _run():
            await asyncio.sleep(1)
            prev_block_hash, response = await self._genesis_invoke(0)
            prev_block_hash, is_commit, tx_result, response = \
                await self._install_sample_token_invoke(1, prev_block_hash)
            self.assertEqual(response, hex(0))
            self.assertEqual(is_commit, True)

            token_addr = tx_result[0]['scoreAddress']
            self.assertEqual(response, hex(0))
            request = {
                "from": "hx0000000000000000000000000000000000000000",
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
        except:
            pass


if __name__ == '__main__':
    unittest.main()
