#!/usr/bin/env python
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
import os
import unittest
from unittest.mock import Mock, patch

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.block import Block
from iconservice.fee.fee_engine import DepositInfo
from iconservice.icon_constant import LATEST_REVISION
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_event_log import EventLogEmitter
from tests.mock_generator import generate_inner_task, clear_inner_task, create_request, ReqData, \
    create_transaction_req

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


def mock_score_invoke(context, to, data_type, data):
    EventLogEmitter.emit_event_log(context, to, 'Transfer(Address,Address,int)',
                                   [Address.from_string(f"hx{'1'*40}"), Address.from_string(f"hx{'2'*40}"), 100], 2)


class TestFeeSharing(unittest.TestCase):

    def setUp(self):
        self._inner_task = generate_inner_task(LATEST_REVISION)
        self.from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        self.to = Address.from_string('cx' + '0' * 40)
        self.score = Address.from_string('cx' + '1' * 40)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def _inner_task_invoke(self, request) -> dict:
        # Clear cached precommit data before calling inner_task._invoke
        self._inner_task._icon_service_engine._precommit_data_manager.clear()
        return self._inner_task._invoke(request)

    def _inner_task_query(self, request) -> dict:
        return self._inner_task._query(request)

    def _validate_transaction(self, request) -> dict:
        return self._inner_task._validate_transaction(request)

    def test_add_deposit(self):
        tx_hash = os.urandom(32)
        tx_hash_hex = bytes.hex(tx_hash)
        term, amount = hex(50), 5000

        mock_score_info = Mock(spec=DepositInfo)
        mock_score_info.configure_mock(sharing_ratio=50)
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = Mock(return_value={})
        self._inner_task._icon_service_engine._fee_engine.can_charge_fee_from_score = Mock()

        self._inner_task._icon_service_engine._fee_engine.add_deposit = Mock(
            return_value=[tx_hash, self.score, self.from_, amount, term])
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = \
            Mock(return_value={self.from_: 9000})

        data = {
            'action': 'add',
            'params': {
                'term': term,
            }
        }

        expected_event_log = [{
            "scoreAddress": str(self.score),
            "indexed": [
                "DepositAdded(bytes,Address,Address,int,int)",
                f"0x{tx_hash_hex}",
                str(self.score),
                str(self.from_)
            ],
            "data": [
                hex(amount),
                term
            ]
        }]

        request = create_request([
            ReqData(tx_hash_hex, self.from_, self.score, amount, 'deposit', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash_hex]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])

        return tx_hash

    def test_withdraw_deposit(self):
        tx_hash = os.urandom(32)
        tx_hash_hex = bytes.hex(tx_hash)
        deposit_id = self.test_add_deposit()
        amount, penalty = 4700, 300

        self._inner_task._icon_service_engine._fee_engine.withdraw_deposit = Mock(
            return_value=(self.score, amount, penalty))
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = \
            Mock(return_value={self.from_: 9000})

        data = {
            'action': 'withdraw',
            'params': {
                'depositId': f"0x{bytes.hex(deposit_id)}"
            }
        }

        expected_event_log = [{
            "scoreAddress": str(self.score),
            "indexed": [
                "DepositWithdrawn(bytes,Address,Address,int,int)",
                f"0x{bytes.hex(deposit_id)}",
                str(self.score),
                str(self.from_)
            ],
            "data": [
                hex(amount),
                hex(penalty)
            ]
        }]

        request = create_request([
            ReqData(tx_hash_hex, self.from_, self.score, 0, 'deposit', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash_hex]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_transaction_result_on_sharing_fee_user_ratio50(self, score_invoke):
        score_invoke.side_effect = mock_score_invoke
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = Mock(return_value={
            self.from_: 9000,
            self.score: 9000
        })
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            "method": "transfer",
            "params": {
                "to": f"hx{'2'*40}",
                "amount": hex(100)
            }
        }

        request = create_request([ReqData(tx_hash, self.from_, str(self.score), 0, "call", data)])
        result = self._inner_task_invoke(request)

        expected_event_log = [{
            "scoreAddress": str(self.score),
            "indexed": [
                'Transfer(Address,Address,int)',
                f"hx{'1'*40}",
                f"hx{'2'*40}"
            ],
            "data": [
                hex(100)
            ]
        }]

        expected_detail_step_used = {
                self.from_: hex(9000),
                self.score: hex(9000)
        }

        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])
        self.assertEqual(expected_detail_step_used, tx_result['stepUsedDetails'])

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_transaction_result_on_sharing_fee_raised_except(self, score_invoke):
        score_invoke.side_effect = mock_score_invoke
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = Mock(return_value={self.from_:0})
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            "method": "transfer",
            "params": {
                "to": f"hx{'2'*40}",
                "amount": hex(100)
            }
        }

        request = create_request([ReqData(tx_hash, self.from_, str(self.score), 0, "call", data)])
        result = self._inner_task_invoke(request)

        expected_event_log = [{
            "scoreAddress": str(self.score),
            "indexed": [
                'Transfer(Address,Address,int)',
                f"hx{'1'*40}",
                f"hx{'2'*40}"
            ],
            "data": [
                hex(100)
            ]
        }]

        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])
        self.assertFalse(tx_result.get('detailStepUsed'))

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_transaction_result_on_sharing_fee_user_ratio100(self, score_invoke):
        score_invoke.side_effect = mock_score_invoke
        self._inner_task._icon_service_engine._fee_engine.charge_transaction_fee = \
            Mock(return_value={self.from_: 9000})
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            "method": "transfer",
            "params": {
                "to": f"hx{'2'*40}",
                "amount": hex(100)
            }
        }

        request = create_request([ReqData(tx_hash, self.from_, str(self.score), 0, "call", data)])
        result = self._inner_task_invoke(request)

        expected_event_log = [{
            "scoreAddress": str(self.score),
            "indexed": [
                'Transfer(Address,Address,int)',
                f"hx{'1'*40}",
                f"hx{'2'*40}"
            ],
            "data": [
                hex(100)
            ]
        }]

        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])
        self.assertFalse(tx_result.get('detailStepUsed'))

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.validate_score_blacklist')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.is_service_flag_on')
    def test_validate_transaction(self, validate_score_blacklist, is_service_flag_on):
        mock_block = Mock(spec=Block)
        mock_block.configure_mock(height=3)
        self._inner_task._icon_service_engine._icx_storage._last_block = mock_block
        self._inner_task._icon_service_engine._icon_pre_validator._is_inactive_score = Mock(return_value=False)
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            "method": "transfer",
            "params": {
                "to": f"hx{'2'*40}",
                "amount": hex(100)
            }
        }

        request = create_transaction_req(ReqData(tx_hash, self.from_, str(self.score), 0, "call", data))
        result = self._validate_transaction(request)
