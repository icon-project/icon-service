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

from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase, TOTAL_SUPPLY

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateFallbackCall(TestIntegrateBase):

    def test_score_pass(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_pass",
                                                                  from_=self._accounts[0])
        score_addr1: 'Address' = tx_results[0].score_address

        value = 1 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=score_addr1,
                          value=value)

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, value)

    def test_score_send_to_eoa(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_to_eoa",
                                                                  from_=self._accounts[0])
        score_addr1: 'Address' = tx_results[0].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_addr_func",
                        params={"addr": str(self._accounts[1].address)})

        value = 1 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=score_addr1,
                          value=value)

        response: int = self.get_balance(self._accounts[1])
        self.assertEqual(response, value)

    def test_score_revert(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_revert",
                                                                  from_=self._accounts[0])
        score_addr1: 'Address' = tx_results[0].score_address

        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.transfer_icx(from_=self._admin,
                                                                  to_=score_addr1,
                                                                  value=value,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "fallback!!")

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_no_payable(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_no_payable",
                                                                  from_=self._accounts[0])
        score_addr1: 'Address' = tx_results[0].score_address

        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.transfer_icx(from_=self._admin,
                                                                  to_=score_addr1,
                                                                  value=value,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_PAYABLE)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not payable"))

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_no_payable_revision_3(self):
        # update governance SCORE(revision4)
        self.update_governance("0_0_4")
        self.set_revision(3)

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_no_payable",
                                                                  from_=self._accounts[0])
        score_addr1: 'Address' = tx_results[0].score_address

        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.transfer_icx(from_=self._admin,
                                                                  to_=score_addr1,
                                                                  value=value,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not found"))

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_pass_link_transfer(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_pass",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_transfer",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})
        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        self.process_confirm_block_tx([tx3, tx4])

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, value)

    def test_score_pass_link_send(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_pass",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        self.process_confirm_block_tx([tx3, tx4])

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, value)

    def test_score_no_payable_link_transfer(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_no_payable",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_transfer",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.METHOD_NOT_PAYABLE)
        self.assertTrue(tx_results[1].failure.message.startswith("Method not payable"))

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_no_payable_link_transfer_revision_3(self):
        # update governance SCORE(revision4)
        self.update_governance("0_0_4")
        self.set_revision(3)

        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_no_payable",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_transfer",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[1].failure.message.startswith("Method not found"))

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_no_payable_link_send(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_no_payable",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "This is not payable")

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_revert_link_transfer(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_revert",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_transfer",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "fallback!!")

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_revert_link_send(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_revert",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "This is not payable")

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_score_revert_link_send_fail(self):
        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_score_revert",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send_fail",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._accounts[0],
                                        to_=score_addr2,
                                        func_name="add_score_func",
                                        params={"score_addr": str(score_addr1)})

        value = 1 * ICX_IN_LOOP
        tx4 = self.create_transfer_icx_tx(from_=self._admin,
                                          to_=score_addr2,
                                          value=value)

        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "Fail icx.send!")

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

    def test_fallback(self):
        response: int = self.get_balance(self._admin)
        self.assertEqual(response, TOTAL_SUPPLY * ICX_IN_LOOP)

        tx1: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send_A",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                                score_name="sample_link_score_send_B",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        score_addr1: 'Address' = tx_results[0].score_address
        score_addr2: 'Address' = tx_results[1].score_address

        tx3 = self.create_score_call_tx(from_=self._admin,
                                        to_=score_addr1,
                                        func_name="add_score_addr",
                                        params={"score_addr": str(score_addr2)})
        tx4 = self.create_score_call_tx(from_=self._admin,
                                        to_=score_addr1,
                                        func_name="add_user_addr",
                                        params={"eoa_addr": str(self._accounts[2].address)})

        tx5 = self.create_score_call_tx(from_=self._admin,
                                        to_=score_addr2,
                                        func_name="add_user_addr1",
                                        params={"eoa_addr": str(self._accounts[3].address)})

        tx6 = self.create_score_call_tx(from_=self._admin,
                                        to_=score_addr2,
                                        func_name="add_user_addr2",
                                        params={"eoa_addr": str(self._accounts[2].address)})

        value = 20 * ICX_IN_LOOP
        tx7 = self.create_transfer_icx_tx(self._admin, score_addr1, value)

        self.process_confirm_block_tx([tx3, tx4, tx5, tx6, tx7])

        response: int = self.get_balance(score_addr1)
        self.assertEqual(response, 0)

        response: int = self.get_balance(score_addr2)
        self.assertEqual(response, 0)

        response: int = self.get_balance(self._accounts[2])
        self.assertEqual(response, 15 * ICX_IN_LOOP)

        response: int = self.get_balance(self._accounts[3])
        self.assertEqual(response, 5 * ICX_IN_LOOP)

    def test_base_fallback_send_0_and_1(self):
        # update governance SCORE(revision4)
        self.update_governance("0_0_4")
        self.set_revision(3)

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_base_fallback",
                                                                  from_=self._accounts[0])
        score_addr: 'Address' = tx_results[0].score_address

        raise_exception_start_tag("sample_base_fallback_send_0_and_1")
        value = 0 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                               to_=score_addr,
                                               value=value)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not found"))

        value = 1 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                               to_=score_addr,
                                               value=value)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not found"))
        raise_exception_end_tag("sample_base_fallback_send_0_and_1")

    def test_non_payable_fallback_send_0_and_1(self):
        # update governance SCORE(revision4)
        self.update_governance("0_0_4")
        self.set_revision(3)

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_non_payable_fallback",
                                                                  from_=self._accounts[0])
        score_addr: 'Address' = tx_results[0].score_address

        raise_exception_start_tag("sample_non_payable_fallback_send_0_and_1")
        value = 0 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                               to_=score_addr,
                                               value=value)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not found"))

        value = 1 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                               to_=score_addr,
                                               value=value)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.METHOD_NOT_FOUND)
        self.assertTrue(tx_results[0].failure.message.startswith("Method not found"))
        raise_exception_end_tag("sample_non_payable_fallback_send_0_and_1")

    def test_payable_external_send_0_and_1(self):
        # update governance SCORE(revision4)
        self.update_governance("0_0_4")
        self.set_revision(3)

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_payable_external",
                                                                  from_=self._accounts[0])
        score_addr: 'Address' = tx_results[0].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr,
                        func_name="set_value1")

        value = 1 * ICX_IN_LOOP
        self.score_call(from_=self._admin,
                        to_=score_addr,
                        func_name="set_value1",
                        value=value)
