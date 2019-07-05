# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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
from unittest.mock import Mock, ANY, patch, MagicMock

from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, InvalidRequestException, \
    InvalidParamsException, OutOfBalanceException
from iconservice.deploy import DeployEngine
from iconservice.fee import FeeEngine
from iconservice.icon_constant import MAX_DATA_SIZE, FIXED_FEE
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.icx import IcxEngine
from tests import create_address


class TestTransactionValidator(unittest.TestCase):

    def setUp(self):
        self.validator = IconPreValidator()

    def test_excute_v2(self):
        self.validator._check_data_size = Mock()
        self.validator._validate_transaction_v2 = Mock()

        self.validator._validate_transaction_v2.reset_mock()
        params = {}
        self.validator.execute(None, params, ANY, ANY)
        self.validator._validate_transaction_v2.assert_called_once_with(None, params)

        self.validator._validate_transaction_v2.reset_mock()
        params = {"version": 2}
        self.validator.execute(None, params, ANY, ANY)
        self.validator._validate_transaction_v2.assert_called_once_with(None, params)

        self.validator._validate_transaction_v2.reset_mock()
        params = {"value": 1}
        self.validator.execute(None, params, ANY, ANY)
        self.validator._validate_transaction_v2.assert_called_once_with(None, params)

        self.validator._validate_transaction_v2.reset_mock()
        params = {"value": -1}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator.execute(None, params, ANY, ANY)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, "value < 0")

        self.validator._validate_transaction_v2.reset_mock()
        params = {"value": 256 * 10 ** 500}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator.execute(None, params, ANY, ANY)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, "exceed ICX amount you can send at one time")

    def _test_excute_v3(self):
        self.validator._check_data_size = Mock()
        self.validator._validate_transaction_v3 = Mock()

        self.validator._validate_transaction_v3.reset_mock()
        params = {"version": 3}
        self.validator.execute(None, params, ANY, ANY)
        self.validator._validate_transaction_v3.assert_called_once_with(params, ANY, ANY)

        self.validator._validate_transaction_v3.reset_mock()
        params = {"version": 3, "value": 1}
        self.validator.execute(None, params, ANY, ANY)
        self.validator._validate_transaction_v3.assert_called_once_with(params, ANY, ANY)

        self.validator._validate_transaction_v3.reset_mock()
        params = {"version": 3, "value": -1}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator.execute(None, params, ANY, ANY)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, "value < 0")

        self.validator._validate_transaction_v2.reset_mock()
        params = {"value": 256 * 10 ** 500}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator.execute(params, ANY, ANY)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, "exceed ICX amount you can send at one time")

    def test_execute_to_check_out_of_balance_v2(self):
        self.validator._check_from_can_charge_fee_v2 = Mock()

        self.validator._check_from_can_charge_fee_v2.reset_mock()
        self.validator.execute_to_check_out_of_balance(None, {}, ANY)
        self.validator._check_from_can_charge_fee_v2.assert_called_once()

        self.validator._check_from_can_charge_fee_v2.reset_mock()
        self.validator.execute_to_check_out_of_balance(None, {"version": 2}, ANY)
        self.validator._check_from_can_charge_fee_v2.assert_called_once()

    def test_execute_to_check_out_of_balance_v3(self):
        self.validator._check_from_can_charge_fee_v3 = Mock()

        self.validator._check_from_can_charge_fee_v3.reset_mock()
        self.validator.execute_to_check_out_of_balance(None, {"version": 3}, ANY)
        self.validator._check_from_can_charge_fee_v3.assert_called_once()

    def test_check_input_data_type(self):
        # flat data with string
        self.validator._check_input_data_type("plain text")

        # flat data with int
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_input_data_type(10000)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # flat data with bool
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_input_data_type(False)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # flat data with float
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_input_data_type(10.1)
            self.assertEqual(e.exception.message, 'Invalid data type')

        params = {
            "method": "transfer",
            "params": {
                "to": "hxab2d8215eab14bc6bdd8bfb2c8151257032ecd8b",
                "value": "0x1"
            }

        }

        # dict data with string
        self.validator._check_input_data_type(params)

        # dict data with int
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'] = 10000
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # dict data with bool
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'] = False
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # dict data with float
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'] = 10.1
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

        params['params']['value'] = ['one', 'two']

        # list data with string
        self.validator._check_input_data_type(params)

        # list data with int
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'][1] = 2
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # list data with bool
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'][1] = False
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

        # list data with float
        with self.assertRaises(InvalidRequestException) as e:
            params['params']['value'][1] = 10.1
            self.validator._check_input_data_type(params)
            self.assertEqual(e.exception.message, 'Invalid data type')

    def test_check_message_data(self):
        self.assert_message_input_raises(None)
        self.assert_message_input_raises({})
        self.assert_message_input_raises([])
        self.assert_message_input_raises(1234)
        self.assert_message_input_raises('message data')
        self.assert_message_input_raises('0x1234ABCD')
        self.validator._check_message_data('0x1234abcd')

    def assert_message_input_raises(self, data):
        with self.assertRaises(InvalidRequestException) as e:
            exception_code = ExceptionCode.ILLEGAL_FORMAT
            exception_message = 'Invalid message data'
            self.validator._check_message_data(data)

        self.assertEqual(e.exception.code, exception_code)
        self.assertEqual(e.exception.message, exception_message)

    def test_check_input_data_size(self):
        self.validator._get_get_data_size = Mock()
        self.validator._check_input_data_size({})

        with patch('iconservice.iconscore.icon_pre_validator.get_input_data_size') as mock:
            mock.return_value = MAX_DATA_SIZE - 1
            self.validator._check_input_data_size({"data": ANY})

        with patch('iconservice.iconscore.icon_pre_validator.get_input_data_size') as mock:
            mock.return_value = MAX_DATA_SIZE
            self.validator._check_input_data_size({"data": ANY})

        with patch('iconservice.iconscore.icon_pre_validator.get_input_data_size') as mock:
            mock.return_value = MAX_DATA_SIZE + 1
            with self.assertRaises(InvalidRequestException) as e:
                self.validator._check_input_data_size({"data": ANY})

                self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
                self.assertEqual(e.exception.message, "Invalid message length")

    def test_check_from_can_charge_fee_v2(self):
        self.validator._check_balance = Mock()

        with self.assertRaises(KeyError) as ke:
            self.validator._check_from_can_charge_fee_v2(None, {})
        self.assertEqual(ke.exception.args[0], "fee")

        invalid_fee = 1
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_from_can_charge_fee_v2(None, {"fee": invalid_fee})
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f"Invalid fee: {invalid_fee}")

        with self.assertRaises(KeyError) as ke:
            self.validator._check_from_can_charge_fee_v2(None, {"fee": FIXED_FEE})
        self.assertEqual(ke.exception.args[0], 'from')

        self.validator._check_balance = Mock()

        fee = FIXED_FEE
        _from = create_address()
        params = {"fee": fee, "from": _from}
        self.validator._check_from_can_charge_fee_v2(None, params)
        self.validator._check_balance.assert_called_once_with(None, _from, 0, fee)

        self.validator._check_balance.reset_mock()
        fee = FIXED_FEE
        _from = create_address()
        value = 12345
        params = {"fee": fee, "from": _from, "value": value}
        self.validator._check_from_can_charge_fee_v2(None, params)
        self.validator._check_balance.assert_called_once_with(None, _from, value, fee)

    def test_validate_transaction_v2(self):
        self.validator._check_from_can_charge_fee_v2 = Mock()
        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._validate_transaction_v2(None, params)
        self.assertEqual(ke.exception.args[0], "to")
        self.validator._check_from_can_charge_fee_v2.assert_called_once_with(None, params)

        self.validator._check_from_can_charge_fee_v2.reset_mock()
        params = {"to": create_address()}
        self.validator._validate_transaction_v2(None, params)
        self.validator._check_from_can_charge_fee_v2.assert_called_once_with(None, params)

        self.validator._check_from_can_charge_fee_v2.reset_mock()
        params = {"to": create_address(1)}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_transaction_v2(None, params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, "Not allowed to transfer coin to SCORE on protocol v2")
        self.validator._check_from_can_charge_fee_v2.assert_called_once_with(None, params)

    def test_validate_transaction_v3(self):
        self.validator._check_minimum_step = Mock()
        self.validator._check_from_can_charge_fee_v3 = Mock()

        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._validate_transaction_v3(None, params, ANY, ANY)
        self.assertEqual(ke.exception.args[0], 'to')

        self.validator._check_minimum_step.asserd_not_called()
        self.validator._check_from_can_charge_fee_v3(None, {}, ANY)

        self.validator._check_minimum_step.reset_mock()
        self.validator._check_from_can_charge_fee_v3.reset_mock()

        self.validator._is_inactive_score = Mock(return_value=True)
        self.validator._get_total_available_step = Mock()
        to = ANY
        params = {"to": to}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_transaction_v3(None, params, ANY, ANY)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'{to} is inactive SCORE')

        self.validator._validate_call_transaction = Mock()
        self.validator._is_inactive_score = Mock(return_value=False)
        params = {"to": ANY, "dataType": "call"}
        self.validator._validate_transaction_v3(None, params, ANY, ANY)
        self.validator._validate_call_transaction.assert_called_once_with(params)

        self.validator._validate_deploy_transaction = Mock()
        self.validator._is_inactive_score = Mock(return_value=False)
        params = {"to": ANY, "dataType": "deploy"}
        self.validator._validate_transaction_v3(None, params, ANY, ANY)
        self.validator._validate_deploy_transaction.assert_called_once_with(params)

        self.validator._validate_call_transaction.reset_mock()
        self.validator._validate_deploy_transaction.reset_mock()
        self.validator._is_inactive_score = Mock(return_value=False)
        params = {"to": ANY}
        self.validator._validate_transaction_v3(None, params, ANY, ANY)
        self.validator._validate_call_transaction.assert_not_called()
        self.validator._validate_deploy_transaction.assert_not_called()

    def test_check_minimum_step(self):
        minimum_step = 100
        params = {}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_minimum_step(params, minimum_step)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, "Step limit too low")

        params = {"stepLimit": minimum_step - 1}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._check_minimum_step(params, minimum_step)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, "Step limit too low")

        params = {"stepLimit": minimum_step}
        self.validator._check_minimum_step(params, minimum_step)

        params = {"stepLimit": minimum_step + 1}
        self.validator._check_minimum_step(params, minimum_step)

    def test_check_from_can_charge_fee_v3(self):
        self.validator._check_balance = Mock()
        step_price = 100

        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._check_from_can_charge_fee_v3(None, params, step_price)
        self.assertEqual(ke.exception.args[0], 'from')
        self.validator._check_balance.assert_not_called()

        self.validator._check_balance.reset_mock()
        _from = create_address()
        to = create_address()
        params = {'from': _from, 'to': to}
        self.validator._check_from_can_charge_fee_v3(None, params, step_price)
        self.validator._check_balance.assert_called_once_with(None, _from, 0, 0)

        self.validator._check_balance.reset_mock()
        _from = create_address()
        value = 123
        step_limit = 456
        fee = step_limit * step_price
        params = {'from': _from, 'to': to, 'value': value, 'stepLimit': step_limit}
        self.validator._check_from_can_charge_fee_v3(None, params, step_price)
        self.validator._check_balance.assert_called_once_with(None, _from, value, fee)

    def test_validate_call_transaction(self):
        self.validator._is_inactive_score = Mock()
        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._validate_call_transaction(params)
        self.assertEqual(ke.exception.args[0], 'to')
        self.validator._is_inactive_score.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = True
        to = create_address()
        params = {'to': to}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_call_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'{to} is inactive SCORE')
        self.validator._is_inactive_score.assert_called_once_with(to)

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        to = create_address(1)
        params = {'to': to}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_call_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'Data not found')
        self.validator._is_inactive_score.assert_called_once_with(to)

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        to = create_address(1)
        params = {'to': to, 'data': {}}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_call_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'Method not found')
        self.validator._is_inactive_score.assert_called_once_with(to)

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        to = create_address(1)
        params = {'to': to, 'data': {'method': ANY}}
        self.validator._validate_call_transaction(params)
        self.validator._is_inactive_score.assert_called_once_with(to)

    def test_validate_deploy_transaction(self):
        self.validator._is_inactive_score = Mock()
        self.validator._validate_new_score_address_on_deploy_transaction = Mock()

        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._validate_deploy_transaction(params)
        self.assertEqual(ke.exception.args[0], 'to')
        self.validator._is_inactive_score.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = True
        self.validator._validate_new_score_address_on_deploy_transaction.reset_mock()
        to = create_address()
        params = {'to': to}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'{to} is an inactive SCORE')
        self.validator._is_inactive_score.assert_called_once_with(to)
        self.validator._validate_new_score_address_on_deploy_transaction.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        self.validator._validate_new_score_address_on_deploy_transaction.reset_mock()
        to = create_address(1)
        params = {'to': to}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'Data not found')
        self.validator._is_inactive_score.assert_called_once_with(to)
        self.validator._validate_new_score_address_on_deploy_transaction.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        self.validator._validate_new_score_address_on_deploy_transaction.reset_mock()
        to = create_address(1)
        params = {'to': to, 'data': {}}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'ContentType not found')
        self.validator._is_inactive_score.assert_called_once_with(to)
        self.validator._validate_new_score_address_on_deploy_transaction.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        self.validator._validate_new_score_address_on_deploy_transaction.reset_mock()
        to = create_address(1)
        params = {'to': to, 'data': {'contentType': ANY}}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'Content not found')
        self.validator._is_inactive_score.assert_called_once_with(to)
        self.validator._validate_new_score_address_on_deploy_transaction.assert_not_called()

        self.validator._is_inactive_score.reset_mock()
        self.validator._is_inactive_score.return_value = False
        self.validator._validate_new_score_address_on_deploy_transaction.reset_mock()
        to = create_address(1)
        params = {'to': to, 'data': {'contentType': ANY, 'content': ANY}}
        self.validator._validate_deploy_transaction(params)
        self.validator._is_inactive_score.assert_called_once_with(to)
        self.validator._validate_new_score_address_on_deploy_transaction.assert_called_once_with(params)

    @patch('iconservice.iconscore.icon_pre_validator.generate_score_address')
    def test_validate_new_score_address_on_deploy_transaction(self, generate_score_address: 'MagicMock'):
        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info = Mock()
        params = {}
        with self.assertRaises(KeyError) as ke:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(ke.exception.args[0], 'to')
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        params = {'to': create_address()}
        self.validator._validate_new_score_address_on_deploy_transaction(params)
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        params = {'dataType': 'deploy', 'to': ZERO_SCORE_ADDRESS}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid params: 'data'")
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        params = {'dataType': 'deploy', 'to': ZERO_SCORE_ADDRESS, 'data': {}}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid params: 'contentType'")
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        content_type = 'invalid'
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'Invalid contentType: {content_type}')
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        content_type = 'application/tbears'
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}}
        self.validator._validate_new_score_address_on_deploy_transaction(params)
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        content_type = 'application/zip'
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid params: 'from'")
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        content_type = 'application/zip'
        _from = create_address()
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}, 'from': _from}
        with self.assertRaises(InvalidParamsException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid params: 'timestamp'")
        generate_score_address.assert_not_called()
        self.validator._deploy_storage.get_deploy_info.assert_not_called()

        generate_score_address.reset_mock()
        score_address = create_address(1)
        generate_score_address.return_value = score_address
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        self.validator._deploy_storage.get_deploy_info.return_value = ANY
        content_type = 'application/zip'
        _from = create_address()
        timestamp = 12345
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}, 'from': _from,
                  'timestamp': timestamp}
        with self.assertRaises(InvalidRequestException) as e:
            self.validator._validate_new_score_address_on_deploy_transaction(params)
        self.assertEqual(e.exception.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(e.exception.message, f'SCORE address already in use: {score_address}')
        generate_score_address.assert_called_once_with(_from, timestamp, ANY)
        self.validator._deploy_storage.get_deploy_info.assert_called_once_with(None, score_address)

        generate_score_address.reset_mock()
        score_address = create_address(1)
        generate_score_address.return_value = score_address
        self.validator._deploy_storage.get_deploy_info.reset_mock()
        self.validator._deploy_storage.get_deploy_info.return_value = None
        content_type = 'application/zip'
        _from = create_address()
        timestamp = 12345
        params = {'to': ZERO_SCORE_ADDRESS, 'data': {'contentType': content_type}, 'from': _from,
                  'timestamp': timestamp}
        self.validator._validate_new_score_address_on_deploy_transaction(params)
        generate_score_address.assert_called_once_with(_from, timestamp, ANY)
        self.validator._deploy_storage.get_deploy_info.assert_called_once_with(None, score_address)

    def test_check_balance(self):
        balance = 200
        self.validator._icx.get_balance = Mock(return_value=balance)
        _from = create_address()
        value = 100
        fee = 10
        self.validator._check_balance(None, _from, value, fee)

        balance = 100
        self.validator._icx.get_balance = Mock(return_value=balance)
        _from = create_address()
        value = 100
        fee = 10
        with self.assertRaises(OutOfBalanceException) as e:
            self.validator._check_balance(None, _from, value, fee)
        self.assertEqual(e.exception.code, ExceptionCode.OUT_OF_BALANCE)
        self.assertEqual(e.exception.message, f"Out of balance: balance({balance}) < value({value}) + fee({fee})")

    def test_is_inactive_score(self):
        address = create_address()
        self.validator._is_score_active = Mock(return_value=True)
        self.assertFalse(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)

        address = create_address()
        self.validator._is_score_active = Mock(return_value=False)
        self.assertFalse(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)

        address = ZERO_SCORE_ADDRESS
        self.validator._is_score_active = Mock(return_value=True)
        self.assertFalse(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)

        address = ZERO_SCORE_ADDRESS
        self.validator._is_score_active = Mock(return_value=False)
        self.assertFalse(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)

        address = create_address(1)
        self.validator._is_score_active = Mock(return_value=True)
        self.assertFalse(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)

        address = create_address(1)
        self.validator._is_score_active = Mock(return_value=False)
        self.assertTrue(self.validator._is_inactive_score(address))
        self.validator._is_score_active.assert_called_once_with(address)
