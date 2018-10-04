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

"""Test for icon_score_base.py and icon_score_base2.py"""

import unittest
import hashlib
import json
from iconservice.base.exception import RevertException
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase
from tests import create_tx_hash, create_address
from tests.integrate_test.test_samples.test_score_api.test_score_base.test_score_base import TestScoreBaseInterface
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateScoreAPI(TestIntegrateBase):

    def _test_deploy_score(self):
        # Deploys test SCORE
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("test_score_base", value1, self._addr_array[0])

        # Uses it when testing `test_get_tx_hashes_by_score_address`
        self.tx_result = tx_result
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        # Asserts if get value is value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", {}, value1)

        # Set value to value2
        value2 = 2 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # Asserts if get value is 2 * value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", {}, value2)

        expect_ret = {}
        self._assert_get_score_status(score_addr1, expect_ret)

        self.score_addr1 = score_addr1

    def setUp(self):
        super().setUp()
        self._test_deploy_score()

    def _deploy_score(self, score_path: str,
                      value: int,
                      from_addr: 'Address',
                      update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("test_score_api",
                                  score_path,
                                  from_addr,
                                  address,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _assert_get_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict, value: Any):
        query_request = {
            "version": self._version,
            "from": from_addr,
            "to": score_addr,
            "dataType": "call",
            "data": {
                "method": func_name,
                "params": params
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value)

    def _get_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict = {}):
        query_request = {
            "version": self._version,
            "from": from_addr,
            "to": score_addr,
            "dataType": "call",
            "data": {
                "method": func_name,
                "params": params
            }
        }
        response = self._query(query_request)
        return response

    def _set_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr,
                                      score_addr,
                                      func_name,
                                      params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertTrue(int(tx_results[0].status))
        self._write_precommit_state(prev_block)

    def _set_value_fail(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr,
                                      score_addr,
                                      func_name,
                                      params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertFalse(int(tx_results[0].status))
        return tx_results[0].failure

    def _assert_get_score_status(self, target_addr: 'Address', expect_status: dict):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def test_revert(self):
        """Checks if the method `revert` raises RevertException successfully."""
        # When readonly is True
        self.assertRaises(RevertException, self._get_value, self._addr_array[0], self.score_addr1, "test_revert_readonly")

        # When readonly is False
        failure = self._set_value_fail(self._addr_array[0], self.score_addr1, "test_revert", {"value": hex(10**18)})
        self.assertEqual(failure.code, 32100)
        self.assertEqual(failure.message, "revert message!!")

    def test_sha3_256(self):
        """Checks if the method `sha3_256` returns digest successfully."""
        # Successful case
        data = b'1234'
        value3 = hashlib.sha3_256(data).digest()
        data = f'0x{bytes.hex(data)}'
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_sha3_256", {'data': data}, value3)

    def test_json_dumps(self):
        """Checks if the method `json_dumps` returns a string of json.dumps data successfully."""
        # Successful case.
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_json_dumps", {}, json.dumps(data))

        # Successful case with none.
        data = {"key1": None, "key2": 2, "key3": "value3"}
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_json_dumps_none", {}, json.dumps(data))

    def test_json_loads(self):
        """Checks if the method `json_dumps` returns a dictionary of json.load data successfully."""
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_json_loads", {}, data)

    def test_is_score_active(self):
        """Checks if the method `is_score_active` returns a bool rightly."""
        # When address is active.
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_is_score_active",
                              {'address': str(self.score_addr1)}, True)

        # When address is inactive.
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_is_score_active",
                               {'address': "cx"+"b"*40}, False)

    def test_get_owner(self):
        """Checks if the method `get_owner` returns the SCORE owner's address."""
        # Successful case.
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_get_owner",
                               {'address': str(self.score_addr1)}, self._addr_array[0])

        # When the SCORE does not exist, returns None.
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_get_owner",
                                   {'address': "cx"+"b"*40}, None)

        # When the address is EOS address not SCORE address.
        self._assert_get_value(self._addr_array[0], self.score_addr1, "test_get_owner",
                                   {'address': str(create_address())}, None)

    def test_create_interface_score(self):
        """Checks if the method `create_interface_score` create the interface score and returns it."""
        return_value = self._get_value(self._addr_array[0], self.score_addr1, "test_create_interface_score",
                               {'address': str(self.score_addr1)})
        self.assertTrue(type(type(return_value)) is type(TestScoreBaseInterface))

    def test_deploy(self):
        """Checks if deploys unsuccessfully with the wrong tx_hash."""
        tx_hash = create_tx_hash()
        tx_hash = f'0x{bytes.hex(tx_hash)}'
        failure = self._set_value_fail(self._addr_array[0], self.score_addr1, "test_deploy",
                                       {'tx_hash': tx_hash})
        self.assertEqual(failure.code, 32000)
        self.assertEqual(failure.message, "Permission Error")

    def test_get_tx_hashes_by_score_address(self):
        """Checks if gets tx_hashes by score address successfully."""
        # When the right SCORE address.
        return_value = self._get_value(self._addr_array[0], self.score_addr1, "test_get_tx_hashes_by_score_address",
                                       {'address': str(self.score_addr1)})
        self.assertEqual(return_value[0], self.tx_result.tx_hash)

        # When the wrong SCORE address.
        return_value = self._get_value(self._addr_array[0], self.score_addr1, "test_get_tx_hashes_by_score_address",
                                       {'address': "cx"+"0"*40})
        self.assertEqual(return_value, (None, None))

        # When the wrong EOS address.
        return_value = self._get_value(self._addr_array[0], self.score_addr1, "test_get_tx_hashes_by_score_address",
                                       {'address': str(create_address())})
        self.assertEqual(return_value, (None, None))

    def test_get_score_address_by_tx_hash(self):
        """Checks if gets score addresses by tx hash successfully."""
        # Successful case.
        tx_hash = f'0x{bytes.hex(self.tx_result.tx_hash)}'
        score_address = self._get_value(self._addr_array[0], self.score_addr1, "test_get_score_address_by_tx_hash",
                                       {'tx_hash': tx_hash})
        self.assertEqual(score_address, self.score_addr1)

        # When the wrong tx_hash.
        tx_hash = f'0x{bytes.hex(create_tx_hash())}'
        score_address = self._get_value(self._addr_array[0], self.score_addr1, "test_get_score_address_by_tx_hash",
                                        {'tx_hash': tx_hash})
        self.assertEqual(score_address, None)


if __name__ == '__main__':
    unittest.main()

