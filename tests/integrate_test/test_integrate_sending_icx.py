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

from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateSendingIcx(TestIntegrateBase):

    def test_send_to_eoa(self):
        # Deploys SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=score_address,
                                                                func_name="send",
                                                                params={'_to': str(self._accounts[1].address),
                                                                        '_amount': hex(value)},
                                                                value=value)
        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(score_address))

        # Checks `_to` balance. It should be 1
        self.assertEqual(value, self.get_balance(self._accounts[1]))

    def test_send_to_eoa_out_of_balance(self):
        # Deploys SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 2 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=score_address,
                                                                func_name="send",
                                                                params={'_to': str(self._accounts[1].address),
                                                                        '_amount': hex(value * 2)},
                                                                value=value)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(self._accounts[1]))

    def test_transfer_to_eoa(self):
        # Deploys SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=score_address,
                                                                func_name="transfer",
                                                                params={'_to': str(self._accounts[1].address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(score_address))

        # Checks `_to` balance. It should be 1
        self.assertEqual(value, self.get_balance(self._accounts[1]))

    def test_transfer_to_eoa_out_of_balance(self):
        # Deploys SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 2 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        self.score_call(from_=self._admin,
                        to_=score_address,
                        func_name="transfer",
                        params={'_to': str(self._accounts[1].address),
                                '_amount': hex(value * 2)},
                        value=value,
                        expected_status=False)

        # Checks SCORE balance. It should be 0, because the transaction is fail
        self.assertEqual(0, self.get_balance(score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(self._accounts[1]))

    def test_send_to_ca(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(receiving_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.send, It should be True
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks sending SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

        # Checks receiving SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(receiving_score_address))

    def test_send_to_ca_out_of_balance(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 2 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(receiving_score_address),
                                                                        '_amount': hex(value * 2)},
                                                                value=value)
        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_send_to_ca_has_no_payable(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_no_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(receiving_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_send_to_ca_has_revert(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_revert",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(receiving_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_transfer_to_ca(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="transfer",
                                                                params={'_to': str(receiving_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks sending SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

        # Checks receiving SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(receiving_score_address))

    def test_transfer_to_ca_out_of_balance(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 2 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        self.score_call(from_=self._admin,
                        to_=sending_score_address,
                        func_name="transfer",
                        params={'_to': str(receiving_score_address),
                                '_amount': hex(value * 2)},
                        value=value,
                        expected_status=False)

        # Checks SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_transfer_to_ca_has_no_payable(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_no_payable",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        self.score_call(from_=self._admin,
                        to_=sending_score_address,
                        func_name="transfer",
                        params={'_to': str(receiving_score_address),
                                '_amount': hex(value)},
                        value=value,
                        expected_status=False)

        # Checks SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_transfer_to_ca_has_revert(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_revert",
                                                                  from_=self._accounts[0])
        receiving_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        self.score_call(from_=self._admin,
                        to_=sending_score_address,
                        func_name="transfer",
                        params={'_to': str(receiving_score_address),
                                '_amount': hex(value)},
                        value=value,
                        expected_status=False)

        # Checks SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

        # Checks `_to` balance. It should be 0
        self.assertEqual(0, self.get_balance(receiving_score_address))

    def test_send_to_self(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(sending_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if the result of icx.send, It should be False
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))

    def test_send_to_self_payable(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send_payable",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="send",
                                                                params={'_to': str(sending_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if `FallbackCalled` exists
        self.assertEqual(tx_results[0].event_logs[1].indexed[0], 'FallbackCalled()')

        # Checks if the result of icx.send, It should be True
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[3].indexed[1], tx_results[0].event_logs[3].indexed[2])

        # Checks SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))

    def test_transfer_to_self(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        self.score_call(from_=self._admin,
                        to_=sending_score_address,
                        func_name="transfer",
                        params={'_to': str(sending_score_address),
                                '_amount': hex(value)},
                        value=value,
                        expected_status=False)

        # Checks sending SCORE balance. It should be 0
        self.assertEqual(0, self.get_balance(sending_score_address))

    def test_transfer_to_self_payable(self):
        # Deploys SCORE, and receiving SCORE
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_score_sending_icx",
                                                                  score_name="sample_score_send_payable",
                                                                  from_=self._accounts[0])
        sending_score_address: 'Address' = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=sending_score_address,
                                                                func_name="transfer",
                                                                params={'_to': str(sending_score_address),
                                                                        '_amount': hex(value)},
                                                                value=value)

        # Checks if `FallbackCalled` exists
        self.assertEqual(tx_results[0].event_logs[1].indexed[0], 'FallbackCalled()')

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[3].indexed[1], tx_results[0].event_logs[3].indexed[2])

        # Checks sending SCORE balance. It should be 1
        self.assertEqual(value, self.get_balance(sending_score_address))
