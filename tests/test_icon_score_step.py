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

import unittest
from typing import Optional
from unittest.mock import patch, Mock

from iconservice.base.address import AddressPrefix, Address
from iconservice.database.db import IconScoreDatabase
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.iconscore.icon_score_base import IconScoreBase, eventlog, \
    external
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_step import StepType
from iconservice.icon_config import Configure
from tests import create_block_hash, create_tx_hash, create_address


class TestIconScoreStepCounter(unittest.TestCase):

    @patch('iconservice.icon_service_engine.'
           'IconServiceEngine.load_builtin_scores')
    @patch('iconservice.database.factory.DatabaseFactory.create_by_name')
    @patch('iconservice.icx.icx_engine.IcxEngine.open')
    def setUp(self, open, create_by_name, load_builtin_scores):
        self._inner_task = IconScoreInnerTask(Configure(""), ".", ".")
        open.assert_called()
        create_by_name.assert_called()
        load_builtin_scores.assert_called()
        self._inner_task._icon_service_engine._icx_engine.get_balance = \
            Mock(return_value=100e18)
        self._inner_task._icon_service_engine._icx_engine._transfer = Mock()

    def tearDown(self):
        self._inner_task = None

    @patch('iconservice.deploy.icon_score_deploy_engine.'
           'IconScoreDeployEngine.invoke')
    @patch('iconservice.icx.icx_engine.IcxEngine.get_balance')
    def test_install_step(self,
                          get_balance,
                          invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = Address.from_string('cx0000000000000000000000000000000000000000')
        content_type = 'application/zip'
        data = {
            'contentType': content_type,
            'content': '0x1867291283973610982301923812873419826abcdef9182731',
        }
        req = self.get_request(tx_hash, to_, 'deploy', data)

        def intercept_get_balance(*args, **kwargs):
            return 100e18

        get_balance.side_effect = intercept_get_balance

        result = self._inner_task._invoke(req)
        input_length = (len(content_type.encode('utf-8')) + 25)
        self.assertEqual(
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.TRANSACTION) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.INSTALL) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.INPUT) * input_length +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.CONTRACT_SET) * 25,
            int(result['txResults'][tx_hash]['stepUsed'], 16))

    def test_transfer_step(self):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.EOA, b'eoa')
        req = self.get_request(tx_hash, to_, None, None)

        result = self._inner_task._invoke(req)
        self.assertEqual(
            self._inner_task._icon_service_engine._step_counter_factory.
                get_step_cost(StepType.TRANSACTION),
            int(result['txResults'][tx_hash]['stepUsed'], 16))

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_internal_transfer_step(self, invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.CONTRACT, b'score')
        req = self.get_request(tx_hash, to_, 'call', {})

        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(context_db))
            score.transfer()

        invoke.side_effect = intercept_invoke

        result = self._inner_task._invoke(req)
        self.assertEqual(
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.TRANSACTION) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.CALL) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.CALL),
            int(result['txResults'][tx_hash]['stepUsed'], 16))

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine.invoke')
    def test_event_log_step(self, invoke):
        tx_hash = bytes.hex(create_tx_hash(b'tx'))
        to_ = create_address(AddressPrefix.CONTRACT, b'score')
        req = self.get_request(tx_hash, to_, 'call', {})

        def intercept_invoke(*args, **kwargs):
            ContextContainer._put_context(args[0])
            context_db = self._inner_task._icon_service_engine._icx_context_db
            score = SampleScore(IconScoreDatabase(context_db))
            address = create_address(AddressPrefix.EOA, b'address')
            i_data_param = b'i_data'
            data_param = b'data'
            text_param = 'text'
            score.SampleEvent(i_data_param, address, data_param, text_param)
            global event_log_data_size
            event_log_data_size = len(
                "SampleEvent(bytes,Address,bytes,str)".encode('utf-8')) + \
                                  len(i_data_param) + \
                                  len(address.body) + \
                                  len(data_param) + \
                                  len(text_param.encode('utf-8'))

        invoke.side_effect = intercept_invoke

        result = self._inner_task._invoke(req)
        self.assertEqual(
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.TRANSACTION) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.CALL) +
            self._inner_task._icon_service_engine._step_counter_factory.
            get_step_cost(StepType.EVENT_LOG) * event_log_data_size,
            int(result['txResults'][tx_hash]['stepUsed'], 16))

    @staticmethod
    def get_request(tx_hash, to_, data_type, data):
        req = {
            'block': {
                'blockHash': bytes.hex(create_block_hash(b'block')),
                'blockHeight': hex(100),
                'timestamp': hex(1234),
                'prevBlockHash': bytes.hex(create_block_hash(b'prevBlock'))
            },
            'transactions': [{
                'method': 'icx_sendTransaction',
                'params': {
                    'txHash': tx_hash,
                    'version': hex(3),
                    'from': str(create_address(AddressPrefix.EOA, b'from')),
                    'to': str(to_),
                    'stepLimit': hex(5000000),
                    'timestamp': hex(123456),
                    'dataType': data_type,
                    'data': data,
                }
            }]
        }
        return req


class SampleScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def get_owner(self,
                  score_address: Optional['Address']) -> Optional['Address']:
        return None

    @eventlog(indexed=2)
    def SampleEvent(
            self, i_data: bytes, address: Address, data: bytes, text: str):
        pass

    @external
    def transfer(self):
        self.icx.transfer(self.msg.sender, 10)

