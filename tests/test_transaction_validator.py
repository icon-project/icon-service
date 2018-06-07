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

from iconservice.base.exception import ExceptionCode
from iconservice.base.address import Address, AddressPrefix, create_address
from iconservice.iconscore.transaction_validator import TransactionValidator


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

        self.tx_validator = TransactionValidator(self.icx_engine)

        self.tx = {
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': create_address(AddressPrefix.CONTRACT, b'to'),
            'value': 0,
            'stepLimit': 100,
            'timestamp': '0x1234567890',
            'nonce': '0x1',
        }

    def tearDown(self):
        self.tx = None
        self.icx_engine = None
        self.tx_validator = None

    def test_check_balance(self):
        step_price = 0
        code, message = self.tx_validator.validate(self.tx, step_price)
        self.assertEqual(ExceptionCode.OK, code)

        self.tx['value'] = 1
        code, message = self.tx_validator.validate(self.tx, step_price)
        self.assertEqual(ExceptionCode.INVALID_REQUEST, code)
        self.assertEqual(message, 'Out of balance')

    def test_check_score_installed(self):
        step_price = 0
        # self.tx['to'] = create_address(AddressPrefix.EOA, b'to')
        code, message = self.tx_validator.validate(self.tx, step_price)
        self.assertEqual(ExceptionCode.OK, code)

        self.icx_engine.storage.score_installed = False
        code, message = self.tx_validator.validate(self.tx, step_price)
        self.assertEqual(ExceptionCode.INVALID_PARAMS, code)
        self.assertEqual('Score not found', message)
