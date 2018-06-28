# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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
from unittest.mock import Mock

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import IconServiceBaseException
from iconservice.base.transaction import Transaction
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.icx import IcxEngine


class TestTransactionResult(unittest.TestCase):
    def setUp(self):
        self._icon_service_engine = IconServiceEngine()
        self._icon_service_engine._icx_engine = Mock(spec=IcxEngine)
        self._icon_service_engine._icon_score_deploy_engine = \
            Mock(spec=IconScoreDeployEngine)

        self._icon_service_engine._icon_score_engine = Mock(
            spec=IconScoreEngine)

        self._mock_context = Mock(spec=IconScoreContext)
        self._mock_context.attach_mock(Mock(spec=Transaction), "tx")
        self._mock_context.attach_mock(Mock(spec=Block), "block")

    def tearDown(self):
        self._icon_service_engine = None
        self._mock_context = None

    def test_tx_success(self):
        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})

        self.assertEqual(1, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(to_, tx_result.to)
        self.assertIsNone(tx_result.score_address)
        dict_as_camel = tx_result.to_response_json()
        self.assertNotIn('failure', dict_as_camel)
        self.assertNotIn('scoreAddress', dict_as_camel)

    def test_tx_failure(self):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=False), 'is_data_type_supported')

        self._icon_service_engine._icon_score_engine. \
            attach_mock(Mock(side_effect=IconServiceBaseException("error")),
                        "invoke")

        from_ = Mock(spec=Address)
        to_ = Mock(spec=Address)
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")
        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context, {'from': from_, 'to': to_})

        self.assertEqual(0, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(to_, tx_result.to)
        self.assertIsNone(tx_result.score_address)
        self.assertNotIn('scoreAddress', tx_result.to_response_json())

    def test_install_result(self):
        self._icon_service_engine._icon_score_deploy_engine.attach_mock(
            Mock(return_value=True), 'is_data_type_supported')

        from_ = Address.from_data(AddressPrefix.EOA, b'test')
        tx_index = Mock(spec=int)
        self._mock_context.tx.attach_mock(tx_index, "index")
        self._mock_context.tx.timestamp = 0
        self._mock_context.tx.origin = from_
        self._mock_context.tx.nonce = None
        tx_result = self._icon_service_engine._handle_icx_send_transaction(
            self._mock_context,
            {
                'from': from_,
                'to': ZERO_SCORE_ADDRESS,
                'dataType': 'deploy',
                'timestamp': 0,
                'data': {
                    'contentType': 'application/tbears',
                    'content': '/home/haha'
                }
            }
        )

        self.assertEqual(1, tx_result.status)
        self.assertEqual(tx_index, tx_result.tx_index)
        self.assertEqual(ZERO_SCORE_ADDRESS, tx_result.to)
        self.assertIsNotNone(tx_result.score_address)
