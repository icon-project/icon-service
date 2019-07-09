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

from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateSendingIcx(TestIntegrateBase):

    def test_send_to_eoa(self):

        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_address,
                'send',
                {'_to': str(self._addr_array[1]), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks SCORE balance. It should be 0
        response = self._query({"address": score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 1
        response = self._query({"address": self._addr_array[1]}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_send_to_eoa_out_of_balance(self):

        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 2 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_address,
                'send',
                {'_to': str(self._addr_array[1]), '_amount': hex(value * 2)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": self._addr_array[1]}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_transfer_to_eoa(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_address,
                'transfer',
                {'_to': str(self._addr_array[1]), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks SCORE balance. It should be 0
        response = self._query({"address": score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 1
        response = self._query({"address": self._addr_array[1]}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_transfer_to_eoa_out_of_balance(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 2 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_address,
                'transfer',
                {'_to': str(self._addr_array[1]), '_amount': hex(value * 2)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be fail
        self.assertEqual(tx_results[0].status, 0)

        # Checks SCORE balance. It should be 0, because the transaction is fail
        response = self._query({"address": score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": self._addr_array[1]}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_send_to_ca(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.send, It should be True
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks sending SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks receiving SCORE balance. It should be 1
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_send_to_ca_out_of_balance(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `send` with 1 ICX then, SCORE sends 2 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(receiving_score_address), '_amount': hex(value * 2)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_send_to_ca_has_no_payable(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_no_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_send_to_ca_has_revert(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_revert",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.send
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_transfer_to_ca(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], tx_results[0].event_logs[2].indexed[2])

        # Checks sending SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks receiving SCORE balance. It should be 1
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_transfer_to_ca_out_of_balance(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 2 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(receiving_score_address), '_amount': hex(value * 2)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be fail
        self.assertEqual(tx_results[0].status, 0)

        # Checks SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_transfer_to_ca_has_no_payable(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_no_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be fail
        self.assertEqual(tx_results[0].status, 0)

        # Checks SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_transfer_to_ca_has_revert(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_revert",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        receiving_score_address = tx_results[1].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(receiving_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be fail
        self.assertEqual(tx_results[0].status, 0)

        # Checks SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Checks `_to` balance. It should be 0
        response = self._query({"address": receiving_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_send_to_self(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(sending_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if the result of icx.send, It should be False
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[1].indexed[1], tx_results[0].event_logs[1].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_send_to_self_payable(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address

        # Calls `send` with 1 ICX then, SCORE sends 1 ICX to `_to`
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'send',
                {'_to': str(sending_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.send, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if `FallbackCalled` exists
        self.assertEqual(tx_results[0].event_logs[1].indexed[0], 'FallbackCalled()')

        # Checks if the result of icx.send, It should be True
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], True)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[3].indexed[1], tx_results[0].event_logs[3].indexed[2])

        # Checks SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_transfer_to_self(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(sending_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be success
        self.assertEqual(tx_results[0].status, 0)

        # Checks sending SCORE balance. It should be 0
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_transfer_to_self_payable(self):
        # Deploys SCORE, and receiving SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("sample_score_sending_icx",
                                 "sample_score_send_payable",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        sending_score_address = tx_results[0].score_address

        # Calls `transfer` with 1 ICX then, SCORE sends 1 ICX to receiving SCORE
        value = 1 * ICX_IN_LOOP
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                sending_score_address,
                'transfer',
                {'_to': str(sending_score_address), '_amount': hex(value)},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result of icx.transfer, The transaction should be success
        self.assertEqual(tx_results[0].status, 1)

        # Checks if `FallbackCalled` exists
        self.assertEqual(tx_results[0].event_logs[1].indexed[0], 'FallbackCalled()')

        # Checks if the result of icx.transfer, It should have no results
        self.assertEqual(tx_results[0].event_logs[2].indexed[1], False)

        # Checks if the msg is rolled back
        self.assertEqual(tx_results[0].event_logs[3].indexed[1], tx_results[0].event_logs[3].indexed[2])

        # Checks sending SCORE balance. It should be 1
        response = self._query({"address": sending_score_address}, 'icx_getBalance')
        self.assertEqual(response, value)


if __name__ == '__main__':
    unittest.main()
