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
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from tests import create_tx_hash, create_address


class MockDeployStorage(object):
    def __init__(self):
        self.score_installed = True

    def is_score_status_active(self, context, icon_score_address: 'Address') -> bool:
        return self.score_installed


class MockIcxEngine(object):
    def __init__(self) -> None:
        self.storage: 'MockIcxStorage' = None
        self.balance: int = 0

    def get_balance(self, context, address: 'Address') -> int:
        return self.balance


class TestTransactionValidator(unittest.TestCase):
    def setUp(self):
        self.deploy_storage = MockDeployStorage()
        self.icx_engine = MockIcxEngine()
        self.validator = IconPreValidator(self.icx_engine, self.deploy_storage)

    def tearDown(self):
        self.icx_engine = None
        self.validator = None

    def test_validate_success(self):
        params = {
            'version': 3,
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': create_address(AddressPrefix.CONTRACT, b'to'),
            'value': 0,
            'stepLimit': 100,
            'timestamp': 123456,
            'nonce': 1
        }

        self.icx_engine.balance = 100
        self.validator.execute(params, step_price=1)

    def test_negative_balance(self):
        step_price = 0
        self.icx_engine.balance = 0

        params = {
            'version': 3,
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': create_address(AddressPrefix.CONTRACT, b'to'),
            'value': -10,
            'stepLimit': 100,
            'timestamp': 123456,
            'nonce': 1
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(params, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('value < 0', cm.exception.message)

    def test_check_balance(self):
        step_price = 0
        self.icx_engine.balance = 0

        params = {
            'version': 3,
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': create_address(AddressPrefix.CONTRACT, b'to'),
            'value': 10,
            'stepLimit': 100,
            'timestamp': 123456,
            'nonce': 1
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(params, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough
        self.icx_engine.balance = 100
        self.validator.execute(params, step_price)

        # too expensive fee
        step_price = 1
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(params, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

    def test_transfer_to_invalid_score_address(self):
        self.icx_engine.balance = 1000
        self.deploy_storage.score_installed = False

        to = create_address(AddressPrefix.CONTRACT, b'to')

        params = {
            'version': 3,
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': to,
            'value': 10,
            'stepLimit': 100,
            'timestamp': 123456,
            'nonce': 1
        }

        # The SCORE indicated by to is not installed
        # Invalid SCORE address
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(params, step_price=1)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual(f'Invalid address: {to}', cm.exception.message)

    # TODO FIXME
    # def test_transfer_to_invalid_eoa_address(self):
    #     self.icx_engine.balance = 1000
    #     self.deploy_storage.score_installed = True
    #
    #     to = create_address(AddressPrefix.EOA, b'to')
    #
    #     params = {
    #         'version': 3,
    #         'txHash': create_tx_hash(b'tx'),
    #         'from': create_address(AddressPrefix.EOA, b'from'),
    #         'to': to,
    #         'value': 10,
    #         'stepLimit': 100,
    #         'timestamp': 123456,
    #         'nonce': 1
    #     }
    #
    #     self.validator.execute(params, step_price=1)
    #
    #     self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
    #     self.assertEqual(f'Invalid address: {to}', cm.exception.message)

    def test_execute_to_check_out_of_balance(self):
        step_price = 10 ** 12
        value = 2 * 10 ** 18
        step_limit = 20000

        self.icx_engine.balance = 0
        self.deploy_storage.score_installed = False

        to = create_address(AddressPrefix.EOA, b'to')

        params = {
            'version': 3,
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': to,
            'value': value,
            'stepLimit': step_limit,
            'timestamp': 1234567890,
            'nonce': 1
        }

        # balance is 0
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute_to_check_out_of_balance(params, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance(value) < value + fee
        self.icx_engine.balance = value

        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute_to_check_out_of_balance(params, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough to pay coin and fee
        self.icx_engine.balance = value + step_limit * step_price
        self.validator.execute_to_check_out_of_balance(params, step_price)


class TestTransactionValidatorV2(unittest.TestCase):
    def setUp(self):
        self.deploy_storage = MockDeployStorage()
        self.icx_engine = MockIcxEngine()
        self.validator = IconPreValidator(self.icx_engine, self.deploy_storage)

    def tearDown(self):
        self.icx_engine = None
        self.tx_validator = None

    def test_out_of_balance(self):
        self.icx_engine.balance = 0
        self.deploy_storage.score_installed = False

        to = create_address(AddressPrefix.EOA, b'to')

        tx = {
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': to,
            'value': 10 * 10 ** 18,
            'fee': 10 ** 16,
            'timestamp': 1234567890,
            'nonce': 1
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx, step_price=0)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # too expensive fee
        self.icx_engine.balance = 10 * 10 ** 18

        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute(tx, step_price=0)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough to pay coin and fee
        self.icx_engine.balance = 10 * 10 ** 18 + 10 ** 16
        self.validator.execute(tx, step_price=0)

    def test_execute_to_check_out_of_balance(self):
        step_price = 10 ** 12
        self.icx_engine.balance = 0
        self.deploy_storage.score_installed = False

        to = create_address(AddressPrefix.EOA, b'to')

        tx = {
            'txHash': create_tx_hash(b'tx'),
            'from': create_address(AddressPrefix.EOA, b'from'),
            'to': to,
            'value': 10 * 10 ** 18,
            'fee': 10 ** 16,
            'timestamp': 1234567890,
            'nonce': 1
        }

        # too small balance
        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute_to_check_out_of_balance(tx, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # too expensive fee
        self.icx_engine.balance = 10 * 10 ** 18

        with self.assertRaises(InvalidRequestException) as cm:
            self.validator.execute_to_check_out_of_balance(tx, step_price)

        self.assertEqual(ExceptionCode.INVALID_REQUEST, cm.exception.code)
        self.assertEqual('Out of balance', cm.exception.message)

        # balance is enough to pay coin and fee
        self.icx_engine.balance = 10 * 10 ** 18 + 10 ** 16
        self.validator.execute_to_check_out_of_balance(tx, step_price)
