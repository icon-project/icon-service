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

import hashlib
import json
from typing import TYPE_CHECKING, List

from iconservice.base.exception import ExceptionCode, AccessDeniedException, IconScoreException
from iconservice.icon_constant import ICX_IN_LOOP
from tests import create_tx_hash, create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateScoreAPI(TestIntegrateBase):

    def _test_deploy_score(self):
        # Deploys test SCORE
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_api",
                                                                  score_name="sample_score_base",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={'value': hex(value1)})
        score_addr1: 'Address' = tx_results[0].score_address

        # Asserts if get value is value1
        response: int = self.query_score(from_=self._accounts[0],
                                         to_=score_addr1,
                                         func_name="get_value",
                                         params={})
        self.assertEqual(value1, response)

        # Set value to value2
        value2 = 2 * ICX_IN_LOOP
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value2)})

        # Asserts if get value is 2 * value2
        response: int = self.query_score(from_=self._accounts[0],
                                         to_=score_addr1,
                                         func_name="get_value",
                                         params={})
        self.assertEqual(value2, response)

        expect_ret = {}
        response: dict = self.get_score_status(score_addr1)
        self.assertEqual(expect_ret, response)
        self.deploy_results: List['TransactionResult'] = tx_results

    def setUp(self):
        super().setUp()
        self._test_deploy_score()

    def test_passed(self):
        pass

    def test_revert(self):
        """Checks if the method `revert` raises IconScoreException successfully."""
        # Successful case - readonly
        with self.assertRaises(IconScoreException) as e:
            self.query_score(from_=self._accounts[0],
                             to_=self.deploy_results[0].score_address,
                             func_name="test_revert_readonly")

        # not readonly
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=self.deploy_results[0].score_address,
                                                                func_name="test_revert",
                                                                params={"value": hex(1 * ICX_IN_LOOP)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "revert message!!")

    def test_sha3_256(self):
        """Checks if the method `sha3_256` returns digest successfully."""
        # Successful case - readonly
        data = b'1234'
        value3 = hashlib.sha3_256(data).digest()
        data = f'0x{bytes.hex(data)}'
        response: bytes = self.query_score(from_=self._accounts[0],
                                           to_=self.deploy_results[0].score_address,
                                           func_name="test_sha3_256_readonly",
                                           params={'data': data})
        self.assertEqual(value3, response)
        # Successful case - not readonly
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_sha3_256",
                        params={'data': data})

    def test_json_dumps(self):
        """Checks if the method `json_dumps` returns a string of json.dumps data successfully."""
        # Successful case - readonly
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        response: str = self.query_score(from_=self._accounts[0],
                                         to_=self.deploy_results[0].score_address,
                                         func_name="test_json_dumps_readonly",
                                         params={})
        self.assertEqual(json.dumps(data), response)

        # Successful case - not readonly
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_json_dumps",
                        params={})

        # Successful case with none
        data = {"key1": None, "key2": 2, "key3": "value3"}
        response: str = self.query_score(from_=self._accounts[0],
                                         to_=self.deploy_results[0].score_address,
                                         func_name="test_json_dumps_none",
                                         params={})
        self.assertEqual(json.dumps(data), response)

    def test_json_loads(self):
        """Checks if the method `json_dumps` returns a dictionary of json.load data successfully."""
        # Successful case - readonly
        data = {"key1": 1, "key2": 2, "key3": "value3"}
        response: dict = self.query_score(from_=self._accounts[0],
                                          to_=self.deploy_results[0].score_address,
                                          func_name="test_json_loads_readonly",
                                          params={})
        self.assertEqual(data, response)

        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_json_loads",
                        params={})

    def test_is_score_active(self):
        """Checks if the method `is_score_active` returns a bool rightly."""
        # Successful case 1 - readonly : When address is active
        response: bool = self.query_score(from_=self._accounts[0],
                                          to_=self.deploy_results[0].score_address,
                                          func_name="test_is_score_active_readonly",
                                          params={'address': str(self.deploy_results[0].score_address)})
        self.assertEqual(True, response)

        # Successful case 2 - readonly : When address is inactive
        response: bool = self.query_score(from_=self._accounts[0],
                                          to_=self.deploy_results[0].score_address,
                                          func_name="test_is_score_active_readonly",
                                          params={'address': "cx" + "b" * 40})
        self.assertEqual(False, response)

        # Successful case - not readonly
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_is_score_active",
                        params={'address': str(self.deploy_results[0].score_address)})

    def test_get_owner(self):
        """Checks if the method `get_owner` returns the SCORE owner's address."""
        # Successful case 1 - readonly
        response: 'Address' = self.query_score(from_=self._accounts[0],
                                               to_=self.deploy_results[0].score_address,
                                               func_name="test_get_owner_readonly",
                                               params={'address': str(self.deploy_results[0].score_address)})
        self.assertEqual(self._accounts[0].address, response)

        # Successful case 2 - readonly : When the SCORE does not exist, returns None.
        response: 'Address' = self.query_score(from_=self._accounts[0],
                                               to_=self.deploy_results[0].score_address,
                                               func_name="test_get_owner_readonly",
                                               params={'address': "cx" + "b" * 40})
        self.assertEqual(None, response)

        # Successful case 3 - readonly : When the address is EOS address not SCORE address.
        response: 'Address' = self.query_score(from_=self._accounts[0],
                                               to_=self.deploy_results[0].score_address,
                                               func_name="test_get_owner_readonly",
                                               params={'address': str(create_address())})
        self.assertEqual(None, response)

        # Successful case - not readonly
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_get_owner",
                        params={'address': str(self.deploy_results[0].score_address)})

    def test_create_interface_score(self):
        """Checks if the method `create_interface_score` create the interface score and returns it."""
        # Successful case - readonly
        response: 'bool' = self.query_score(from_=self._accounts[0],
                                            to_=self.deploy_results[0].score_address,
                                            func_name="test_create_interface_score_readonly",
                                            params={'address': str(self.deploy_results[0].score_address)})
        self.assertEqual(True, response)

        # Successful case 1 - not readonly
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_create_interface_score",
                        params={'address': str(self.deploy_results[0].score_address)})

        # Successful case 2 - not readonly
        # If the SCORE does not exist, it can pass the test.
        # Creating an interface SCORE means mapping the interface with the SCORE.
        self.score_call(from_=self._accounts[0],
                        to_=self.deploy_results[0].score_address,
                        func_name="test_create_interface_score",
                        params={'address': "cx" + "b" * 40})

    def test_deploy(self):
        """Checks if deploys unsuccessfully with the wrong tx_hash."""
        tx_hash = create_tx_hash()
        tx_hash = f'0x{bytes.hex(tx_hash)}'

        # Failure case - readonly
        with self.assertRaises(AccessDeniedException) as e:
            self.query_score(from_=self._accounts[0],
                             to_=self.deploy_results[0].score_address,
                             func_name="test_deploy_readonly",
                             params={'tx_hash': tx_hash})

        # Failure case - not readonly
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=self.deploy_results[0].score_address,
                                                                func_name="test_deploy",
                                                                params={'tx_hash': tx_hash},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[0].failure.message, "No permission")

    def test_get_tx_hashes_by_score_address(self):
        """Checks if gets tx_hashes by score address successfully."""
        # Successful case 1 - readonly : When the right SCORE address.
        response: tuple = self.query_score(from_=self._accounts[0],
                                           to_=self.deploy_results[0].score_address,
                                           func_name="test_get_tx_hashes_by_score_address_readonly",
                                           params={'address': str(self.deploy_results[0].score_address)})
        self.assertEqual(self.deploy_results[0].tx_hash, response[0])

        response: tuple = self.query_score(from_=self._accounts[0],
                                           to_=self.deploy_results[0].score_address,
                                           func_name="test_get_tx_hashes_by_score_address_readonly",
                                           params={'address': str(self.deploy_results[0].score_address)})

        self.assertEqual(self.deploy_results[0].tx_hash, response[0])

        # Successful case 2 - readonly : When the wrong SCORE address.
        response: tuple = self.query_score(from_=self._accounts[0],
                                           to_=self.deploy_results[0].score_address,
                                           func_name="test_get_tx_hashes_by_score_address_readonly",
                                           params={'address': "cx" + "0" * 40})
        self.assertEqual((None, None), response)

        # Successful case 3 - readonly : When the wrong EOS address.
        response: tuple = self.query_score(from_=self._accounts[0],
                                           to_=self.deploy_results[0].score_address,
                                           func_name="test_get_tx_hashes_by_score_address_readonly",
                                           params={'address': str(create_address())})
        self.assertEqual((None, None), response)

        # Successful case 1 - not readonly
        self.score_call(
            from_=self._accounts[0],
            to_=self.deploy_results[0].score_address,
            func_name="test_get_tx_hashes_by_score_address",
            params={'address': str(self.deploy_results[0].score_address)})

        # Successful case 2 - not readonly
        self.score_call(
            from_=self._accounts[0],
            to_=self.deploy_results[0].score_address,
            func_name="test_get_tx_hashes_by_score_address",
            params={'address': "cx" + "b" * 40})

    def test_get_score_address_by_tx_hash(self):
        """Checks if gets score addresses by tx hash successfully."""
        # Successful case 1 - readonly
        tx_hash_right = f'0x{bytes.hex(self.deploy_results[0].tx_hash)}'
        response: 'Address' = self.query_score(from_=self._accounts[0],
                                               to_=self.deploy_results[0].score_address,
                                               func_name="test_get_score_address_by_tx_hash_readonly",
                                               params={'tx_hash': tx_hash_right})
        self.assertEqual(self.deploy_results[0].score_address, response)

        # Successful case 2 - readonly : When the wrong tx_hash.
        tx_hash_wrong = f'0x{bytes.hex(create_tx_hash())}'
        response: 'Address' = self.query_score(from_=self._accounts[0],
                                               to_=self.deploy_results[0].score_address,
                                               func_name="test_get_score_address_by_tx_hash_readonly",
                                               params={'tx_hash': tx_hash_wrong})
        self.assertEqual(None, response)

        # Successful case 1 - not readonly
        self.score_call(
            from_=self._accounts[0],
            to_=self.deploy_results[0].score_address,
            func_name="test_get_score_address_by_tx_hash",
            params={'tx_hash': tx_hash_right})

        # Successful case 2 - not readonly : When the wrong tx_hash.
        self.score_call(
            from_=self._accounts[0],
            to_=self.deploy_results[0].score_address,
            func_name="test_get_score_address_by_tx_hash",
            params={'tx_hash': tx_hash_wrong})
