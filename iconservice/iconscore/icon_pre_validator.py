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

from ..base.exception import InvalidParamsException, InvalidRequestException
from ..base.address import Address
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..icx.icx_engine import IcxEngine
    from ..iconscore.icon_score_context import IconScoreContext


class IconPreValidator:
    class JsonRpcMessageValidator:

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
                cls, key: str, params: dict, optional: bool = False) -> None:
            if optional and key not in params:
                return

            address = params.get(key)
            if not isinstance(address, Address):
                raise InvalidParamsException(
                    message=f'Invalid address: {key}')

        @classmethod
        def _check_int_value(
                cls, key: str, params: dict, optional: bool = False) -> int:
            # If key is optional and params doesn't contain key, do nothing
            if optional and key not in params:
                return 0

            int_value = params.get(key)
            if not isinstance(int_value, int):
                raise InvalidParamsException(
                    message=f'Invalid param: {int_value}')

        @classmethod
        def _check_data_value(
                cls, data_type: str, data: dict, optional: bool = False):
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
                raise InvalidParamsException(
                    message=f"'{key}' not found")

    """IconService Pre Validator
    """

    def __init__(self, icx: 'IcxEngine') -> None:
        """Constructor

        :param icx: icx engine
        """
        self._icx = icx

    def validate_tx(self, context: 'IconScoreContext', converted_tx: dict, step_price: int) -> None:
        """Validate a transaction before accepting it
                If failed to validate a tx, client will get a json-rpc error response

                :param context: query context
                :param converted_tx: dict including tx info
                :param step_price:
                """

        self._validate_tx(converted_tx)
        self._icx_check_balance(context, converted_tx, step_price)
        self._icx_check_to_address(context, converted_tx)

    @staticmethod
    def validate_query(converted_tx: dict) -> None:
        method = converted_tx['method']
        params = converted_tx['params']
        IconPreValidator.JsonRpcMessageValidator.validate(method, params)

    @staticmethod
    def _validate_tx(request: dict) -> None:
        IconPreValidator._check_contain_dict('method', request)
        method = request['method']
        IconPreValidator._check_contain_dict('params', request)
        params = request['params']
        IconPreValidator._check_contain_dict('txHash', params)

        IconPreValidator.JsonRpcMessageValidator.validate(method, params)

    @staticmethod
    def _check_contain_dict(key, table: dict) -> None:
        if key not in table:
            raise InvalidParamsException(
                message=f"'{key}' not found")

    def _icx_check_balance(self, context: 'IconScoreContext', tx: dict, step_price: int) -> None:
        """Check the balance of from address is enough to pay for tx fee and value

        :param tx:
        :param step_price:
        """
        tx = tx['params']

        _from = tx['from']
        value = tx.get('value', 0)
        step_limit = tx.get('stepLimit', 0)
        balance = self._icx.get_balance(context=context, address=_from)

        if balance < value + step_limit * step_price:
            raise InvalidRequestException('Out of balance')

    def _icx_check_to_address(self, context: 'IconScoreContext', tx: dict) -> None:
        """Check the validation of to

        :param tx:
        :return:
        """
        tx = tx['params']
        to = tx.get('to', None)

        if to is None:
            pass
        elif to and not isinstance(to, Address):
            Address.from_string(to)
        elif to.is_contract and not self._icx.storage.is_score_installed(context=context, icon_score_address=to):
            raise InvalidParamsException(f'Score is not installed {str(to)}')

