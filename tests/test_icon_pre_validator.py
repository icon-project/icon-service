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
        self.validator = IconPreValidator(
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

    def test_validate_success(self):
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

        self.validator.execute(tx)

    def test_check_balance(self):
        self.icx_engine.balance = 0

        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': create_address(AddressPrefix.CONTRACT, b'to'),
                'value': 10,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': 1
            }
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough
        self.icx_engine.balance = 100
        self.validator.execute(tx)

        # too expensive fee
        self.validator.step_price = 1
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

    def test_transfer_to_invalid_score_address(self):
        self.validator.step_price = 1
        self.icx_engine.balance = 1000
        self.icx_engine.storage.score_installed = False

        to = create_address(AddressPrefix.CONTRACT, b'to')

        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': to,
                'value': 10,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': 1
            }
        }

        # The SCORE indicated by to is not installed
        # Invalid SCORE address
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual(f'Invalid address: {to}', cm.exception.message)

    def test_transfer_to_invalid_eoa_address(self):
        self.validator.step_price = 1
        self.icx_engine.balance = 1000
        self.icx_engine.storage.score_installed = True

        to = create_address(AddressPrefix.EOA, b'to')

        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': to,
                'value': 10,
                'stepLimit': 100,
                'timestamp': 123456,
                'nonce': 1
            }
        }

        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual(f'Invalid address: {to}', cm.exception.message)


class TestTransactionValidatorV2(unittest.TestCase):
    def setUp(self):
        icx_storage = MockIcxStorage()
        self.icx_engine = MockIcxEngine()
        self.icx_engine.storage = icx_storage
        self.validator = IconPreValidator(
            self.icx_engine, step_price=0)

    def tearDown(self):
        self.icx_engine = None
        self.tx_validator = None

    def test_out_of_balance(self):
        self.icx_engine.balance = 0
        self.icx_engine.storage.score_installed = False

        to = create_address(AddressPrefix.EOA, b'to')

        tx = {
            'method': 'icx_sendTransaction',
            'params': {
                'txHash': create_tx_hash(b'tx'),
                'from': create_address(AddressPrefix.EOA, b'from'),
                'to': to,
                'value': 10 * 10 ** 18,
                'fee': 10 ** 16,
                'timestamp': 1234567890,
                'nonce': 1
            }
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # too expensive fee
        self.icx_engine.balance = 10 * 10 ** 18

        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough to pay coin and fee
        self.icx_engine.balance = 10 * 10 ** 18 + 10 ** 16
        self.validator.execute(tx)
