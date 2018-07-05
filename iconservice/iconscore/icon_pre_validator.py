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

from typing import TYPE_CHECKING

from ..base.address import Address, AddressPrefix
from ..base.exception import InvalidRequestException

if TYPE_CHECKING:
    from ..icx.icx_engine import IcxEngine


class IconPreValidator:
    """Validate icx_sendTransaction request before putting it into tx pool
    """

    def __init__(self, icx: 'IcxEngine', step_price: int) -> None:
        """Constructor

        :param icx: icx engine
        """
        self._handlers = {
            'icx_sendTransaction': self._validate_send_transaction
        }

        self._icx = icx
        self.step_price = step_price

    def execute(self, request: dict) -> None:
        """Validate a JSON-RPC request before passing it into IconServiceEngine
        If failed to validate the request, raise an exception

        Assume that values in request have been already converted
        to original format (string -> int, string -> Address, etc)

        :param request: JSON-RPC request
        """
        method = request.get('method')
        if method not in self._handlers:
            raise InvalidRequestException(f'Unsupported method: {method}')

        handler = self._handlers[method]

        params = request.get('params', {})
        handler(params)

    def _validate_send_transaction(self, params: dict) -> None:
        data_type = params.get('dataType', None)

        version: int = params.get('version', 2)

        if version < 3:
            self._validate_transfer_transaction_v2(params)
        else:
            if data_type == 'call':
                self._validate_call_transaction(params)
            elif data_type == 'deploy':
                self._validate_deploy_transaction(params)
            else:
                self._check_balance_v3(params)

    def _validate_transfer_transaction_v2(self, params: dict):
        """

        :param params:
        :return:
        """
        self._check_to_address_v2(params)
        self._check_balance_v2(params)

    def _validate_call_transaction(self, params: dict):
        """Validate call transaction
        It is not icx_call

        :param params:
        :return:
        """
        to: 'Address' = params['to']

        if not self._is_score_address(to):
            raise InvalidRequestException(f'{to} is not a SCORE address')

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise InvalidRequestException(f'data not found')

        if 'method' not in data:
            raise InvalidRequestException(f'method not found')

    def _validate_deploy_transaction(self, params: dict):
        to: 'Address' = params['to']

        if not self._is_score_address(to):
            raise InvalidRequestException(f'{to} is not a SCORE address')

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise InvalidRequestException(f'data not found')

        if 'contentType' not in data:
            raise InvalidRequestException(f'contentType not found')

        if 'content' not in data:
            raise InvalidRequestException(f'content not found')

    def _check_balance_v2(self, params: dict) -> None:
        """Check the balance of from address is enough
        to pay for tx fee and value

        It supports coin transfer based on both protocol v2 and v3

        :param params:
        """
        from_: 'Address' = params['from']
        value: int = params.get('value', 0)
        fee: int = params['fee']

        self._check_balance(from_, value, fee)

    def _check_balance_v3(self, params: dict) -> None:
        """Check the balance of from address is enough
        to pay for tx fee and value

        It supports coin transfer based on both protocol v2 and v3

        :param params:
        """
        from_: 'Address' = params['from']
        value: int = params.get('value', 0)

        step_limit = params.get('stepLimit', 0)
        fee = step_limit * self.step_price

        self._check_balance(from_, value, fee)

    def _check_to_address_v2(self, params: dict) -> None:
        """Prevent transfer coin to SCORE using protocol v2

        Check to address prefix mistake
        JSON-RPC Server has already checked 'hx' prefix of to address

        :param params:
        :return:
        """
        to: 'Address' = params['to']
        score_address = Address(AddressPrefix.CONTRACT, to.body)

        if self._icx.storage.is_score_installed(
                context=None, icon_score_address=score_address):
            raise InvalidRequestException(
                'It is not allowed to transfer coin to SCORE on protocol v2')

    def _check_balance(self, from_: 'Address', value: int, fee: int):
        balance = self._icx.get_balance(context=None, address=from_)

        if balance < value + fee:
            raise InvalidRequestException('Out of balance')

    def _is_score_address(self, address: 'Address') -> bool:
        """Check the validation of to address

        :param address:
        :return:
        """
        return address.is_contract and \
            self._icx.storage.is_score_installed(None, address)
