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

from iconservice.base.address import MalformedAddress
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateSimpleInvoke(TestIntegrateBase):

    def test_ise_get_status(self):
        request = {'filter': ['lastBlock']}
        response = self._query(request, 'ise_getStatus')
        last_block = response['lastBlock']

        self.assertEqual(last_block['blockHeight'], 0)

        self.assertTrue('blockHash' in last_block)
        self.assertTrue(isinstance(last_block['blockHash'], bytes))
        self.assertEqual(len(last_block['blockHash']), 32)

        self.assertTrue('prevBlockHash' in last_block)
        self.assertEqual(last_block['prevBlockHash'], None)

        self.assertTrue('timestamp' in last_block)
        self.assertTrue(isinstance(last_block['timestamp'], int))
        self.assertTrue(last_block['timestamp'])

    def test_ise_get_status2(self):
        request = {}
        response = self._query(request, 'ise_getStatus')
        last_block = response['lastBlock']

        self.assertEqual(last_block['blockHeight'], 0)

        self.assertTrue('blockHash' in last_block)
        self.assertTrue(isinstance(last_block['blockHash'], bytes))
        self.assertEqual(len(last_block['blockHash']), 32)

        self.assertTrue('prevBlockHash' in last_block)
        self.assertEqual(last_block['prevBlockHash'], None)

        self.assertTrue('timestamp' in last_block)
        self.assertTrue(isinstance(last_block['timestamp'], int))
        self.assertTrue(last_block['timestamp'])

    def test_invoke_success(self):
        value1 = 3 * ICX_IN_LOOP
        tx1 = self._make_icx_send_tx(self._genesis, self._addr_array[0], value1)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        value2 = 2 * ICX_IN_LOOP
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], value2)

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        query_request = {
            "address": self._addr_array[0]
        }
        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value1 - value2)

        query_request = {
            "address": self._addr_array[1]
        }
        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value2)

    def test_make_invalid_block_height(self):
        value1 = 1 * ICX_IN_LOOP

        # have to NextBlockHeight[2] != LastBlockHeight[0] + 1 (32000)

        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], value1)
        with self.assertRaises(BaseException) as e:
            self._make_and_req_block([tx], block_height=0)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIn(f"Failed to invoke a block", e.exception.message)

        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], value1)
        with self.assertRaises(BaseException) as e:
            self._make_and_req_block([tx], block_height=2)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIn(f"Failed to invoke a block", e.exception.message)

        query_request = {
            "address": self._addr_array[0]
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_make_invalid_block_hash(self):
        value1 = 1 * ICX_IN_LOOP

        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], value1)
        prev_block, tx_results = self._make_and_req_block([tx], block_height=1)

        # modulate blockHash
        invalid_block = self._create_invalid_block(prev_block.height)
        with self.assertRaises(BaseException) as e:
            self._write_precommit_state(invalid_block)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIn("No precommit data:", e.exception.message)

        query_request = {
            "address": self._addr_array[0]
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_send_icx_using_malformed_address1(self):
        value1 = 1 * ICX_IN_LOOP

        malformed_address = MalformedAddress.from_string("hx1234")
        tx = self._make_icx_send_tx(self._genesis, malformed_address, value1,
                                    disable_pre_validate=True, support_v2=True)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        query_request = {
            "address": malformed_address
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value1)

    def test_send_icx_using_malformed_address2(self):
        value1 = 1 * ICX_IN_LOOP

        malformed_address = MalformedAddress.from_string("11")
        tx = self._make_icx_send_tx(self._genesis, malformed_address, value1,
                                    disable_pre_validate=True, support_v2=True)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        query_request = {
            "address": malformed_address
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value1)


if __name__ == '__main__':
    unittest.main()
