# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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


from iconservice.icon_constant import REV_IISS, \
    IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSBaseTransactionRevision(TestIISSBase):

    def _create_dummy_tx(self):
        return self._make_icx_send_tx(self._genesis, self._admin, 0)

    def _create_dummy_base_transaction(self):
        dummy_base_transacion = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'timestamp': 1561972402347409,
                'dataType': 'base',
                'data': {
                    'prep': {'irep': 37500, 'rrep': 800, 'totalDelegation': 0, 'value': 0},
                    'result': {'coveredByFee': 0, 'coveredByOverIssuedICX': 0, 'issue': 0}
                },
                'txHash': 'c2f208be9a5d99beae36ff9a6abd27123e4faafc0d0de28ebb01738ce5ef2b20'}
        }
        return dummy_base_transacion

    def test_base_transaction_under_rev_iiss(self):
        # success case: when isBlockEditable is false, block which does not have base tx should be invoked successfully.
        tx_list = [
            self._create_dummy_tx()
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=False)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        self.assertEqual(expected_tx_status, tx_results[0].status)

        # success case: when isBlockEditable is true, block which does not have base tx should be invoked successfully.
        tx_list = [
            self._create_dummy_tx(),
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=True)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        self.assertEqual(expected_tx_status, tx_results[0].status)

        # failure case: when isBlockEditable is false, block which has base tx should be failed to invoke.
        tx_list_with_base_transaction = [
            self._create_dummy_base_transaction(),
            self._create_dummy_tx()
        ]
        self.assertRaises(KeyError,
                          self._make_and_req_block_for_issue_test,
                          tx_list_with_base_transaction, None, None, None, True, 0)

    def test_base_transaction_between_rev_iiss_and_rev_decentralization(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # success case: when isBlockEditable is false, block which does not have base tx should be invoked successfully.
        tx_list = [
            self._create_dummy_tx()
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=False)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        self.assertEqual(expected_tx_status, tx_results[0].status)

        # success case: when isBlockEditable is true, block which does not have base tx should be invoked successfully.
        tx_list = [
            self._create_dummy_tx(),
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=True)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        self.assertEqual(expected_tx_status, tx_results[0].status)

        # failure case: when isBlockEditable is false, block which has base tx should be failed to invoke.
        tx_list_with_base_transaction = [
            self._create_dummy_base_transaction(),
            self._create_dummy_tx()
        ]
        self.assertRaises(KeyError,
                          self._make_and_req_block_for_issue_test,
                          tx_list_with_base_transaction, None, None, None, True, 0)

