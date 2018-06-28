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

from iconservice.base.exception import ExceptionCode, InvalidRequestException, InvalidParamsException
from iconservice.base.address import AddressPrefix
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from tests import create_tx_hash, create_address


class MockIcxStorage(object):
    def __init__(self):
        self.score_installed = True

    def is_score_installed(self, context, icon_score_address: 'Address') -> bool:
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

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)

        self.icon_pre_validator = IconPreValidator(self.icx_engine)

        self.tx = {
            'method': 'test',
            'params': {
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': create_address(AddressPrefix.CONTRACT, b'to'),
                'value': 0,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': '0x1'
            }
        }

    def tearDown(self):
        self.tx = None
        self.icx_engine = None
        self.tx_validator = None

    def test_check_balance(self):
        step_price = 0
        try:
            self.icon_pre_validator.validate_tx(self._context, self.tx, step_price)
        except:
            self.fail('raise exception!')

        response = {}
        try:
            self.tx['params']['value'] = 1
            self.icon_pre_validator.validate_tx(self._context, self.tx, step_price)
        except InvalidRequestException as e:
            response = {'code': e.code, 'message': e.message}

        self.assertEqual(ExceptionCode.INVALID_REQUEST, response['code'])
        self.assertEqual(response['message'], 'Out of balance')

    def test_check_score_installed(self):
        step_price = 0
        try:
            self.icon_pre_validator.validate_tx(self._context, self.tx, step_price)
        except:
            self.fail('raise exception!')

        self.icx_engine.storage.score_installed = False
        response = {}
        try:
            self.icon_pre_validator.validate_tx(self._context, self.tx, step_price)
        except InvalidParamsException as e:
            response = {'code': e.code, 'message': e.message}

        self.assertEqual(ExceptionCode.INVALID_PARAMS, response['code'])
        self.assertEqual(response['message'],
                         f"Score is not installed {create_address(AddressPrefix.CONTRACT, b'to')}")
