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

from iconservice.base.address import AddressPrefix
from iconservice.base.exception import ExceptionCode, InvalidRequestException
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from tests import create_tx_hash, create_address


class MockIcxStorage(object):
    def __init__(self):
        self.score_installed = True

    def is_score_installed(self, context,
                           icon_score_address: 'Address') -> bool:
        return self.score_installed


class MockIcxEngine(object):
    def __init__(self) -> None:
        self.storage: 'MockIcxStorage' = None
        self.balance: int = 0

    def get_balance(self, context, address: 'Address') -> int:
        return self.balance


class TestTransactionValidator(unittest.TestCase):
    def setUp(self):
        icx_storage = MockIcxStorage()
        self.icx_engine = MockIcxEngine()
        self.icx_engine.storage = icx_storage
        self._context = None
        self.icon_pre_validator = IconPreValidator(
            self.icx_engine, step_price=0)

        self.tx = {
            'method': 'test',
            'params': {
                'version': 3,
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': create_address(AddressPrefix.CONTRACT, b'to'),
                'value': 0,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': 1
            }
        }

    def tearDown(self):
        self.tx = None
        self.icx_engine = None
        self.tx_validator = None

    def test_validate_success_v3(self):
        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': create_address(AddressPrefix.CONTRACT, b'to'),
                'value': 0,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': 1
            }
        }

        self.icon_pre_validator.execute(tx)

    def test_check_balance(self):
        try:
            self.icon_pre_validator.execute(self.tx)
        except:
            self.fail('raise exception!')

        response = {}
        try:
            self.tx['params']['value'] = 1
            self.icon_pre_validator.execute(self.tx)
        except InvalidRequestException as e:
            response = {'code': e.code, 'message': e.message}

        self.assertEqual(ExceptionCode.INVALID_REQUEST, response['code'])
        self.assertEqual(response['message'], 'Out of balance')

    def test_check_score_installed(self):
        try:
            self.icon_pre_validator.execute(self.tx)
        except:
            self.fail('raise exception!')

        self.icx_engine.storage.score_installed = False
        response = {}
        try:
            self.icon_pre_validator.execute(self.tx)
        except InvalidParamsException as e:
            response = {'code': e.code, 'message': e.message}

        self.assertEqual(ExceptionCode.INVALID_PARAMS, response['code'])
        self.assertEqual(response['message'],
                         f"Score is not installed {create_address(AddressPrefix.CONTRACT, b'to')}")
