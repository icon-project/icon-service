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
from iconservice.base.exception import ExceptionCode, DatabaseException, StackOverflowException
from iconservice.icon_constant import ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateScoreInternalCall(TestIntegrateBase):

    def test_link_score(self):
        value1 = 1 * ICX_IN_LOOP
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS,
                                                deploy_params={'value': hex(value1)})

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="add_score_func",
                        params={"score_addr": str(score_addr1)})

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value1)

        value2 = 2 * ICX_IN_LOOP
        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="set_value",
                        params={"value": hex(value2)})

        response = self._query(query_request)
        self.assertEqual(response, value2)

    def test_link_score_cross(self):
        value1 = 1 * ICX_IN_LOOP
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS,
                                                deploy_params={'value': hex(value1)})

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_score_cross",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="add_score_func",
                        params={"score_addr": str(score_addr1)})

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        with self.assertRaises(DatabaseException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(e.exception.message, "No permission to write")

        value2 = 2 * ICX_IN_LOOP
        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="set_value",
                        params={"value": hex(value2)})

    def test_link_score_loop(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_loop",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_loop",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3: dict = self.create_score_call_tx(from_=self._accounts[0],
                                              to_=score_addr2,
                                              func_name="add_score_func",
                                              params={"score_addr": str(score_addr1)})

        tx4: dict = self.create_score_call_tx(from_=self._accounts[0],
                                              to_=score_addr1,
                                              func_name="add_score_func",
                                              params={"score_addr": str(score_addr2)})

        self.process_confirm_block_tx([tx3, tx4])

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        with self.assertRaises(StackOverflowException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.message, 'Max call stack size exceeded')

        value2 = 2 * ICX_IN_LOOP
        raise_exception_start_tag("sample_link_score_loop")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr2,
                                                                func_name="set_value",
                                                                params={"value": hex(value2)},
                                                                expected_status=False)
        raise_exception_end_tag("sample_link_score_loop")
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    def test_get_other_score_db(self):
        value1 = 1 * ICX_IN_LOOP
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS,
                                                deploy_params={'value': hex(value1)})

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="add_score_func",
                        params={"score_addr": str(score_addr1)})

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_data_from_other_score", "params": {}
            }
        }
        self._query(query_request)  # Query method does not raise AccessDenied exception

        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="try_get_other_score_db",
                        params={},
                        expected_status=False)

    def test_transfer_via_internal_call(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        # callee SCORE = score_addr1
        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="add_score_func",
                        params={"score_addr": str(score_addr1)})

        value = 2 * ICX_IN_LOOP

        # increase balance of score_addr2
        self.transfer_icx(self._admin, score_addr2, value)
        balance: int = self.get_balance(score_addr2)
        self.assertEqual(value, balance)

        # transfer value from score_addr2 to score_addr1
        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="transfer_icx_to_other_score",
                        params={"value": hex(value)})

        balance = self.get_balance(score_addr1)
        self.assertEqual(value, balance, balance)
        balance = self.get_balance(score_addr2)
        self.assertEqual(0, balance, balance)

        # transfer fallbacked balance(value) from score_addr2 to score_addr1 in one TX
        self.score_call(from_=self._admin,
                        to_=score_addr2,
                        value=value,
                        func_name="transfer_all_icx_to_other_score")

        balance = self.get_balance(score_addr1)
        self.assertEqual(value * 2, balance, balance)
        balance = self.get_balance(score_addr2)
        self.assertEqual(0, balance, balance)

    def test_transfer_via_internal_call_error(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx2: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_link_score",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        # callee SCORE = score_addr1
        self.score_call(from_=self._accounts[0],
                        to_=score_addr2,
                        func_name="add_score_func",
                        params={"score_addr": str(score_addr1)})

        value = 2 * ICX_IN_LOOP

        # transfer without balance
        tx_results = self.score_call(from_=self._accounts[0],
                                     to_=score_addr2,
                                     func_name="transfer_icx_to_other_score",
                                     params={"value": hex(value)},
                                     expected_status=False)
        self.assertTrue(tx_results[0].failure.message.startswith("Out of balance"))

        # increase balance of score_addr2
        self.transfer_icx(self._admin, score_addr2, value)
        balance: int = self.get_balance(score_addr2)
        self.assertEqual(value, balance)

        # transfer via not payable external function
        tx_results = self.score_call(from_=self._accounts[0],
                                     to_=score_addr2,
                                     func_name="transfer_icx_to_other_score_fail",
                                     params={"value": hex(value)},
                                     expected_status=False)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not payable"))

    def test_invalid_interface_score(self):
        tx: dict = self.create_deploy_score_tx(
            score_root="invalid_interface_score",
            score_name="sample_invalid_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS
        )
        self.process_confirm_block_tx([tx], expected_status=False)

        tx1: dict = self.create_deploy_score_tx(
            score_root="invalid_interface_score",
            score_name="sample_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS
        )

        tx2: dict = self.create_deploy_score_tx(
            score_root="invalid_interface_score",
            score_name="sample_link_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS
        )

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        # callee SCORE = score_addr1
        self.score_call(
            from_=self._accounts[0],
            to_=score_addr2,
            func_name="add_score_func",
            params={"score_addr": str(score_addr1)}
        )

        value = 1
        amount = 2 * ICX_IN_LOOP

        tx_results = self.score_call(
            from_=self._accounts[0],
            to_=score_addr2,
            func_name="test_func_params_int_with_icx",
            params={"value": hex(value), "amount": hex(amount)},
            expected_status=False
        )
        self.assertTrue(tx_results[0].failure.message.startswith("Out of balance"))

        # increase balance of score_addr2
        self.transfer_icx(self._admin, score_addr2, value)
        balance: int = self.get_balance(score_addr2)
        self.assertEqual(value, balance)

        self.score_call(
            from_=self._accounts[0],
            to_=score_addr2,
            func_name="test_func_params_int_with_icx",
            params={"value": hex(value), "amount": hex(amount)}
        )
