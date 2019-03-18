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

from iconservice.base.address import AddressPrefix, Address
from iconservice.icon_constant import LATEST_REVISION
from iconservice.iconscore.icon_score_context import ContextContainer
from tests.mock_generator import generate_inner_task, clear_inner_task, create_request, ReqData

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestFeeSharing(unittest.TestCase):

    def setUp(self):
        self._inner_task = generate_inner_task(LATEST_REVISION)

    def tearDown(self):
        ContextContainer._clear_context()
        clear_inner_task()

    def _inner_task_invoke(self, request) -> dict:
        # Clear cached precommit data before calling inner_task._invoke
        self._inner_task._icon_service_engine._precommit_data_manager.clear()
        return self._inner_task._invoke(request)

    def test_set_fee_share(self):
        tx_hash = bytes.hex(os.urandom(32))
        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to = Address.from_string('cx' + '0' * 40)
        score = Address.from_string('cx' + '1' * 40)
        data = {
            'method': 'setFeeShare',
            'params': {
                '_score': str(score),
                '_ratio': 50
            }
        }

        request = create_request([
            ReqData(tx_hash, from_, to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])

    def test_get_fee_share(self):
        pass

    def test_create_deposit(self):
        tx_hash = bytes.hex(os.urandom(32))
        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to = Address.from_string('cx' + '0' * 40)
        score = Address.from_string('cx' + '1' * 40)
        data = {
            'method': 'createDeposit',
            'params': {
                '_score': str(score),
                '_term': 50
            }
        }

        request = create_request([
            ReqData(tx_hash, from_, to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])
        self.assertEqual()

        return tx_hash

    def test_destroy_deposit(self):
        deposit_id = self.test_create_deposit()

        tx_hash = bytes.hex(os.urandom(32))
        from_ = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        to = Address.from_string('cx' + '0' * 40)
        score = Address.from_string('cx' + '1' * 40)
        data = {
            'method': 'destroyDeposit',
            'params': {
                '_id': deposit_id
            }
        }

        request = create_request([
            ReqData(tx_hash, from_, to, 'call', data),
        ])

        result = self._inner_task_invoke(request)
        tx_result = result['txResults'][tx_hash]

        self.assertEqual('0x1', tx_result['status'])

    def test_get_deposit(self):
        pass

    def test_get_score_info(self):
        pass

    def test_available_steps(self):
        pass

    def test_pre_validate_on_sharing_fee(self):
        pass

    def test_transaction_result_on_sharing_fee(self):
        pass
