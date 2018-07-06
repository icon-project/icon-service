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

from ..base.address import Address
from ..base.exception import InvalidRequestException
from ..icon_config import FIXED_FEE

if TYPE_CHECKING:
    from ..icx.icx_engine import IcxEngine


class IconPreValidator:
    """Validate only icx_sendTransaction request before putting it into tx pool

    It does not validate query requests like icx_getBalance, icx_call and so on
    """

    def __init__(self, icx: 'IcxEngine') -> None:
        """Constructor

        :param icx: icx engine
        """
        self._icx = icx

    def execute(self, params: dict, step_price: int) -> None:
        """Validate a transaction on icx_sendTransaction
        If failed to validate a tx, raise an exception

        Assume that values in params have already been converted
        to original format (string -> int, string -> Address, etc)

        :param params: params of icx_sendTransaction JSON-RPC request
        :param step_price:
        """
        version: int = params.get('version', 2)
        if version < 3:
            self._validate_transaction_v2(params)
        else:
            self._validate_transaction_v3(params, step_price)

    def execute_to_check_out_of_balance(
            self, params: dict, step_price: int) -> None:
        version: int = params.get('version', 2)

        if version < 3:
            self._check_from_can_charge_fee_v2(params)
        else:
            self._check_from_can_charge_fee_v3(params, step_price)

    def _check_from_can_charge_fee_v2(self, params: dict):
        fee: int = params['fee']
        if fee != FIXED_FEE:
            raise InvalidRequestException(f'Invalid fee: {fee}')

        from_: 'Address' = params['from']
        value: int = params.get('value', 0)

        self._check_balance(from_, value, fee)

    def _validate_transaction_v2(self, params: dict):
        """Validate transfer transaction based on protocol v2

        :param params:
        :return:
        """
        # Check out of balance
        self._check_from_can_charge_fee_v2(params)

        # Check 'to' is not a SCORE address
        to: 'Address' = params['to']
        if self._icx.storage.is_score_installed(
                context=None, icon_score_address=to):
            raise InvalidRequestException(
                'It is not allowed to transfer coin to SCORE on protocol v2')

    def _validate_transaction_v3(self, params: dict, step_price: int):
        """Validate transfer transaction based on protocol v2

        :param params:
        :return:
        """
        self._check_from_can_charge_fee_v3(params, step_price)

        # Check if "to" address is valid
        to: 'Address' = params['to']

        if to.is_contract and not self._icx.storage.is_score_installed(
                context=None, icon_score_address=to):
            raise InvalidRequestException(f'Invalid address: {to}')

        if not to.is_contract and self._icx.storage.is_score_installed(
                context=None, icon_score_address=to):
            raise InvalidRequestException(f'Invalid address: {to}')

        # Check data_type-specific elements
        data_type = params.get('dataType', None)
        if data_type == 'call':
            self._validate_call_transaction(params)
        elif data_type == 'deploy':
            self._validate_deploy_transaction(params)

    def _check_from_can_charge_fee_v3(self, params: dict, step_price: int):
        from_: 'Address' = params['from']
        value: int = params.get('value', 0)

        step_limit = params.get('stepLimit', 0)
        fee = step_limit * step_price

        self._check_balance(from_, value, fee)

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

    def _check_balance(self, from_: 'Address', value: int, fee: int):
        balance = self._icx.get_balance(context=None, address=from_)

        if balance < value + fee:
            raise InvalidRequestException('Out of balance')

    def _is_score_address(self, address: 'Address') -> bool:
        return address.is_contract and self._icx.storage.is_score_installed(
            context=None, icon_score_address=address)
