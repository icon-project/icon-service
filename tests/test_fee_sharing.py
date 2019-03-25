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
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.fee.fee_manager import FeeManager, ScoreInfo
from iconservice.icon_constant import LATEST_REVISION
from iconservice.iconscore.icon_score_context import ContextContainer
from tests.mock_generator import generate_inner_task, clear_inner_task, create_request, ReqData, create_query_request, \
    QueryData

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


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

    def test_set_fee_share(self):
        mock_set_ratio = Mock()
        mock_score_info = Mock(spec=ScoreInfo)
        mock_score_info.configure_mock(sharing_ratio=50)
        self._inner_task._icon_service_engine._fee_manager.set_fee_sharing_ratio = mock_set_ratio
        self._inner_task._icon_service_engine._fee_manager.charge_transaction_fee = Mock(return_value={})
        self._inner_task._icon_service_engine._fee_manager.get_score_fee_info = Mock(return_value=mock_score_info)
        self._inner_task._icon_service_engine._fee_manager.can_charge_fee_from_score = Mock()

        ratio = hex(50)
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            'method': 'setRatio',
            'params': {
                '_score': str(self.score),
                '_ratio': ratio
            }
        }

        expected_event_logs = [{
            "scoreAddress": str(self.to),
            "indexed": [
                "FeeShareSet(Address,int)",
                str(self.score),
            ],
            "data": [
                ratio
            ]
        }]

        request = create_request([
            ReqData(tx_hash, self.from_, self.to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual(expected_event_logs, tx_result['eventLogs'])
        self.assertEqual('0x1', tx_result['status'])

        mock_set_ratio.assert_called()

        return ratio

    def test_get_fee_share(self):
        ratio = self.test_set_fee_share()

        data = {
            "method": "getFeeShare",
            "params": {
                "_score": str(self.score)
            }
        }

        expected_response = {
            "ratio": ratio
        }

        request = create_query_request(QueryData(self.from_, self.to, "call", data))
        result = self._inner_task_query(request)

        self.assertEqual(expected_response, result)

    def test_create_deposit(self):
        mock_score_info = Mock(spec=ScoreInfo)
        mock_score_info.configure_mock(sharing_ratio=50)
        self._inner_task._icon_service_engine._fee_manager.deposit_fee = Mock()
        self._inner_task._icon_service_engine._fee_manager.charge_transaction_fee = Mock(return_value={})
        self._inner_task._icon_service_engine._fee_manager.get_score_fee_info = Mock(return_value=mock_score_info)
        self._inner_task._icon_service_engine._fee_manager.can_charge_fee_from_score = Mock()

        tx_hash = bytes.hex(os.urandom(32))
        term, amount = hex(50), hex(5000)
        data = {
            'method': 'createDeposit',
            'params': {
                '_score': str(self.score),
                '_term': term,
                '_amount': amount
            }
        }

        expected_event_log = [{
            "scoreAddress": str(self.to),
            "indexed": [
                "DepositCreated(bytes,Address,Address,int,int)",
                f"0x{tx_hash}",
                str(self.score),
                str(self.from_)
            ],
            "data": [
                amount,
                term
            ]
        }]

        request = create_request([
            ReqData(tx_hash, self.from_, self.to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])

        return tx_hash

    def test_destroy_deposit(self):
        deposit_id = self.test_create_deposit()
        amount, penalty = 4700, 300

        tx_hash = bytes.hex(os.urandom(32))

        data = {
            'method': 'destroyDeposit',
            'params': {
                '_id': deposit_id
            }
        }

        expected_event_log = {
            "scoreAddress": str(self.to),
            "indexed": [
                "DepositDestroyed(bytes,Address,Address,int,int)",
                deposit_id,
                str(self.score),
                str(self.from_)
            ],
            "data": [
                hex(amount),
                hex(penalty)
            ]
        }

        request = create_request([
            ReqData(tx_hash, self.from_, self.to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_event_log, tx_result['eventLogs'])

    def test_get_deposit(self):
        deposit_id = self.test_create_deposit()
        current_block_height = 100

        data = {
            'method': 'getDeposit',
            'params': {
                '_id': deposit_id
            }
        }

        expected_result = {
            "_id": deposit_id,
            "_score": str(self.score),
            "_from": str(self.from_),
            "amount": hex(5000),
            "_createdAt": f"{hex(current_block_height)}",
            "_expiresIn": f"{hex(current_block_height+50)}",
            "_virtualStepIssued": "f(d,a)",
            "_virtualStepUsed": "used vs"
        }
        request = create_query_request(QueryData(self.from_, self.to, "call", data))

        result = self._inner_task_query(request)

        self.assertEqual(expected_result, result)

    def test_get_score_info(self):
        self.test_set_fee_share()
        deposit_id = self.test_create_deposit()
        current_block_height = 100

        data = {
            'method': "getScoreInfo",
            "params": {
                "_score": str(self.score)
            }
        }

        expected_result = {
            "_address": str(self.score),
            "_totalVirtualStepIssued": hex(5000),
            "_totalVirtualStepUsed": hex(0),
            "_deposits": [
                {
                    "_id": deposit_id,
                    "_score": str(self.score),
                    "_from": str(self.from_),
                    "amount": hex(5000),
                    "_createdAt": f"{current_block_height}",
                    "_expiresIn": f"{current_block_height + 50}",
                    "_virtualStepIssued": "f(d,a)",
                    "_virtualStepUsed": "used vs"
                 }
            ]
        }

        request = create_query_request(QueryData(self.from_, self.to, "call", data))
        result = self._inner_task_query(request)
        self.assertEqual(expected_result, result)

    def test_available_steps(self):
        self.test_set_fee_share()
        self.test_create_deposit()

        data = {
            'method': "availableStep",
            "params": {
                "_score": str(self.score)
            }
        }

        expected_result = {
            "availableStep": hex(5000)
        }

        request = create_query_request(QueryData(self.from_, self.to, "call", data))
        result = self._inner_task_query(request)
        self.assertEqual(expected_result, result)

    def test_transaction_result_on_sharing_fee(self):
        fee_manager = Mock(spec=FeeManager)
        fee_manager.charge_transaction_fee = Mock(return_value=(1200, 2))
        self.test_set_fee_share()
        self.test_create_deposit()
        tx_hash = bytes.hex(os.urandom(32))

        data = {
            "method": "transfer",
            "params": {
                "_to": f"hx{'2'*40}",
                "_amount": hex(100)
            }
        }

        request = create_request([ReqData(tx_hash, self.from_, str(self.score), "call", data)])
        result = self._inner_task_invoke(request)

        expected_event_log = {
            "scoreAddress": str(self.score),
            "indexed": [
                "Transfer(Address,Address,int)",
                str(self.from_),
                f"hx{'2'*40}"
            ],
            "data": [
                hex(100)
            ]
        }

        expected_detail_step_used = [
            {
                "address": str(self.from_),
                "stepUsed": hex(9000)
            },
            {
                "address": str(self.score),
                "stepUsed": hex(9000)
            }
        ]

        tx_result = result['txResults'][tx_hash]

        self.assertEqual(expected_event_log, tx_result['eventLogs'])
        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual(expected_detail_step_used, tx_result['detailStepUsed'])

