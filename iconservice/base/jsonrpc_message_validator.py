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


from .address import is_icon_address_valid
from .exception import ExceptionCode, IconException


class JsonRpcMessageValidator(object):

    @classmethod
    def validate(cls, method: str, params: dict) -> None:
        """Validate json-rpc message
        If json-rpc message is not valid, raise an exception
       
        :param method:
        :param params: json-rpc params before type converting
        :return:
        """
        if method == 'icx_getBalance':
            cls.validate_get_balance(params)
        elif method == 'icx_call':
            cls.validate_call(params)
        elif method == 'icx_sendTransaction':
            cls.validate_send_transaction(params)

    @classmethod
    def validate_get_balance(cls, params: dict) -> None:
        cls._check_contains('address', params)

    @classmethod
    def validate_call(cls, params: dict) -> None:
        cls._check_address_value('from', params)

    @classmethod
    def validate_send_transaction(cls, params: dict) -> None:
        cls._check_address_value('from', params)

        data_type = params.get('dataType', None)

        if data_type == 'call':
            cls._validate_call_on_send_transaction(params)
        elif data_type == 'install':
            cls._validate_install_on_send_transaction(params)
        elif data_type == 'update':
            cls._validate_update_on_send_transaction(params)
        else:
            cls._validate_transfer_on_send_transaction(params)

    @classmethod
    def _validate_call_on_send_transaction(cls, params):
        cls._check_address_value('from', params)
        cls._check_int_value('value', params, optional=True)

    @classmethod
    def _validate_transfer_on_send_transaction(cls, params):
        cls._check_address_value('from', params)
        cls._check_address_value('to', params)
        cls._check_int_value('timestamp', params)

    @classmethod
    def _validate_update_on_send_transaction(cls, params):
        cls._check_address_value('from', params)
        cls._check_address_value('to', params)

    @classmethod
    def _validate_install_on_send_transaction(cls, params):
        cls._check_address_value('from', params)

    @classmethod
    def _check_address_value(
            cls, key: str, params: dict, optional: bool=False) -> None:
        if optional and key not in params:
            return

        address: str = params.get(key)
        if not is_icon_address_valid(address):
            raise IconException(
                code=ExceptionCode.INVALID_PARAMS,
                message=f'Invalid address: {key}')

    @classmethod
    def _check_int_value(
            cls, key: str, params: dict, optional: bool=False) -> int:
        # If key is optional and params doesn't contain key, do nothing
        if optional and key not in params:
            return 0

        try:
            return int(params[key], 16)
        except Exception as e:
            raise IconException(
                code=ExceptionCode.INVALID_PARAMS,
                message=f'Invalid param: {repr(e)}')

    @classmethod
    def _check_data_value(
            cls, data_type: str, data: dict, optional: bool=False):
        """

        :param data_type:
        :param data:
        :param optional:
        :return:
        """
        pass

    @classmethod
    def _check_contains(cls, key: str, params: dict):
        if key not in params:
            raise IconException(
                code=ExceptionCode.INVALID_PARAMS,
                message=f"'{key}' not found")