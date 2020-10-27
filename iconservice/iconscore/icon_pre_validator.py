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

from typing import TYPE_CHECKING, Any, Optional

from iconcommons.logger import Logger

from .icon_score_step import get_input_data_size

from ..base.address import Address, AddressPrefix, SYSTEM_SCORE_ADDRESS, generate_score_address, is_icon_address_valid
from ..base.exception import InvalidRequestException, InvalidParamsException, OutOfBalanceException
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import (
    FIXED_FEE, MAX_DATA_SIZE, DEFAULT_BYTE_SIZE,
    DATA_BYTE_ORDER, Revision, DeployState, DataType
)
from ..utils import is_lowercase_hex_string
from ..utils.locked import is_address_locked

if TYPE_CHECKING:
    from ..deploy.storage import IconScoreDeployInfo
    from .icon_score_context import IconScoreContext


TAG = "PV"
REQUEST_PARAMS = (
    ConstantKeys.VERSION,
    ConstantKeys.STEP_LIMIT,
    ConstantKeys.NID,
    ConstantKeys.TIMESTAMP,
    ConstantKeys.VALUE,
    ConstantKeys.NONCE,
    ConstantKeys.FROM,
    ConstantKeys.TO,
    ConstantKeys.SIGNATURE,
    ConstantKeys.DATA_TYPE,
    ConstantKeys.DATA,
)

REQUIRED_PARAMS = (
    ConstantKeys.VERSION,
    ConstantKeys.STEP_LIMIT,
    ConstantKeys.NID,
    ConstantKeys.TIMESTAMP,
    ConstantKeys.FROM,
    ConstantKeys.TO,
    ConstantKeys.SIGNATURE
)

INT_PARAMS = (
    ConstantKeys.VERSION,
    ConstantKeys.STEP_LIMIT,
    ConstantKeys.NID,
    ConstantKeys.TIMESTAMP,
    ConstantKeys.VALUE,
    ConstantKeys.NONCE
)

ADDR_PARAMS = (
    ConstantKeys.FROM,
    ConstantKeys.TO
)


class IconPreValidator:
    """Validate only icx_sendTransaction request before putting it into tx pool

    It does not validate query requests like icx_getBalance, icx_call and so on
    """

    def __init__(self) -> None:
        """Constructor
        """
        pass

    def origin_request_execute(self, params: dict, revision: int):
        if revision < Revision.IMPROVED_PRE_VALIDATOR.value:
            return
        self.origin_pre_validate_version(params)
        self.origin_pre_validate_params(params)
        self.origin_validate_fields(params)

    def origin_validate_fields(self, params: dict):
        for param, value in params.items():
            self.origin_validate_param(param)
            self.origin_validate_value(param, value)

    @classmethod
    def origin_pre_validate_version(cls, params: dict):
        version: str = params.get(ConstantKeys.VERSION, None)
        if version != '0x3':
            raise InvalidRequestException(f'Invalid message version, got {version}')

    @classmethod
    def origin_pre_validate_params(cls, params: dict):
        if len(params) > len(REQUEST_PARAMS):
            raise InvalidRequestException('Unexpected Parameters')

        required_results = [
            required_key
            for required_key
            in REQUIRED_PARAMS
            if required_key not in params
        ]

        if required_results:
            raise InvalidRequestException(
                f'Not included required parameters, missing parameters {required_results}'
            )

    @classmethod
    def origin_validate_param(cls, param: str):
        if param not in REQUEST_PARAMS:
            raise InvalidParamsException(f'Unexpected Parameters, got {param}')

    @classmethod
    def origin_validate_value(cls, param: str, value: str):
        if param in INT_PARAMS:
            if not cls.is_integer_type(value):
                raise InvalidRequestException(f'Unexpected INT Type, got {value}')
        elif param in ADDR_PARAMS:
            if not cls.is_address_type(value):
                raise InvalidRequestException(f'Unexpected Address Type, got {value}')

    @classmethod
    def is_integer_type(cls, value: str) -> bool:
        try:
            if value.startswith('0x'):
                return value == hex(int(value, 16))
        except ValueError:
            return False
        else:
            return False

    @classmethod
    def is_address_type(cls, value: str) -> bool:
        return is_icon_address_valid(value)

    def execute(self, context: 'IconScoreContext', params: dict, step_price: int, minimum_step: int):
        """Validate a transaction on icx_sendTransaction
        If failed to validate a tx, raise an exception

        Assume that values in params have already been converted
        to original format (string -> int, string -> Address, etc)

        :param context:
        :param params: params of icx_sendTransaction JSON-RPC request
        :param step_price:
        :param minimum_step: minimum step
        """

        self._check_input_data(params)

        value: int = params.get('value', 0)
        if value < 0:
            raise InvalidParamsException("value < 0")
        try:
            value.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER)
        except OverflowError:
            raise InvalidParamsException("exceed ICX amount you can send at one time")

        version: int = params.get('version', 2)
        if version < 3:
            self._validate_transaction_v2(context, params)
        else:
            self._validate_transaction_v3(context, params, step_price, minimum_step)

    def execute_to_check_out_of_balance(self, context: 'IconScoreContext', params: dict, step_price: int):
        version: int = params.get('version', 2)

        if version < 3:
            self._check_from_can_charge_fee_v2(context, params)
        else:
            self._check_from_can_charge_fee_v3(context, params, step_price)

    @staticmethod
    def _check_input_data(params: dict):
        """
        Validates input data. It checks the input data type and the input data size.

        :param params: params of icx_sendTransaction JSON-RPC request
        :return:
        """

        input_data = params.get('data', None)
        if 'message' == params.get('dataType', None):
            IconPreValidator._check_message_data(input_data)
        else:
            IconPreValidator._check_input_data_type(input_data)

        IconPreValidator._check_input_data_size(input_data)

    @staticmethod
    def _check_message_data(data: Any):
        """
        Check if the message data is a lowercase hex string

        :param data: input data of message type
        """
        if isinstance(data, str) \
                and data.startswith('0x') \
                and is_lowercase_hex_string(data[2:]) \
                and len(data) % 2 == 0:
            return

        raise InvalidRequestException('Invalid message data')

    @staticmethod
    def _check_input_data_type(data: Any):
        """
        Validates transaction data types whether the leaf fields are str or None
        """
        if isinstance(data, dict):
            for v in data.values():
                IconPreValidator._check_input_data_type(v)
        elif isinstance(data, list):
            for v in data:
                IconPreValidator._check_input_data_type(v)
        elif data is not None and not isinstance(data, str):
            # The leaf value should be None or str.
            raise InvalidRequestException('Invalid data type')

    @staticmethod
    def _check_input_data_size(input_data: Any):
        """
        Validates transaction data whether total bytes is less than MAX_DATA_SIZE
        If the property is a key-value object, counts key and value.

        Assume that values in params have already been converted
        to original format (string -> int, string -> Address, etc)
        But the field of 'data' has not been converted (TypeConvert marks it as LATER)

        :param input_data: data field of icx_sendTransaction JSON-RPC request
        """

        if input_data is not None:
            size = get_input_data_size(Revision.LATEST.value, input_data)

            if size > MAX_DATA_SIZE:
                raise InvalidRequestException('Invalid message length')

    def _check_from_can_charge_fee_v2(self, context: 'IconScoreContext', params: dict):
        fee: int = params['fee']
        if fee != FIXED_FEE:
            raise InvalidRequestException(f'Invalid fee: {fee}')

        from_: 'Address' = params['from']
        value: int = params.get('value', 0)

        self._check_balance(context, from_, value, fee)

    def _validate_transaction_v2(self, context: 'IconScoreContext', params: dict):
        """Validate transfer transaction based on protocol v2

        :param params:
        :return:
        """
        # Check out of balance
        self._check_from_can_charge_fee_v2(context, params)

        # Check 'to' is not a SCORE address
        to: 'Address' = params['to']
        if to.is_contract:
            raise InvalidRequestException(
                'Not allowed to transfer coin to SCORE on protocol v2')

    def _validate_transaction_v3(self, context: 'IconScoreContext', params: dict, step_price: int, minimum_step: int):
        """Validate transfer transaction based on protocol v3

        :param params:
        :return:
        """
        self._check_minimum_step(params, minimum_step)
        self._check_from_can_charge_fee_v3(context, params, step_price)

        # Check if "to" address is valid
        to: 'Address' = params['to']

        if self._is_inactive_score(context, to):
            raise InvalidRequestException(f'{to} is inactive SCORE')

        # Check data_type-specific elements
        data_type = params.get('dataType', None)
        self.validate_data_type(context, to, data_type)

        if data_type == DataType.CALL:
            self._validate_call_transaction(context, params)
        elif data_type == DataType.DEPLOY:
            self._validate_deploy_transaction(context, params)
        elif data_type == DataType.DEPOSIT:
            self._validate_deposit_transaction(context, params)

    @staticmethod
    def _check_minimum_step(params: dict, minimum_step: int):
        step_limit = params.get('stepLimit', 0)
        if step_limit < minimum_step:
            raise InvalidRequestException('Step limit too low')

    def _check_from_can_charge_fee_v3(self, context: 'IconScoreContext', params: dict, step_price: int):
        from_: 'Address' = params['from']
        to: 'Address' = params['to']
        value: int = params.get('value', 0)

        step_limit = params.get('stepLimit', 0)
        fee = step_limit * step_price

        self._check_balance(context, from_, value, fee)

        data_type: str = params.get('dataType')
        if to.is_contract and data_type in (None, 'call', 'message'):
            # Check if the SCORE can be called when fee-sharing ON.
            # If data_type is None or message and the recipient is SCORE,
            # it works like `call`.(calling fallback)
            context.engine.fee.check_score_available(context, to, context.block.height)

    @staticmethod
    def validate_data_type(
            context: 'IconScoreContext', to: 'Address', data_type: Optional[str]):
        if context.revision < Revision.IMPROVED_PRE_VALIDATOR.value:
            return

        if not DataType.contains(data_type):
            raise InvalidParamsException(f"Invalid dataType: {data_type}")

        if to.prefix == AddressPrefix.EOA and data_type not in (None, DataType.MESSAGE):
            raise InvalidParamsException(
                f"Mismatch between to and dataType: to={to}, dataType={data_type}"
            )

    def _validate_call_transaction(self, context: 'IconScoreContext', params: dict):
        """Validate call transaction
        It is not icx_call

        :param params:
        :return:
        """
        to: 'Address' = params['to']

        if self._is_inactive_score(context, to):
            raise InvalidRequestException(f'{to} is inactive SCORE')

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise InvalidRequestException('Data not found')

        if 'method' not in data:
            raise InvalidRequestException('Method not found')

    def _validate_deploy_transaction(self, context: 'IconScoreContext', params: dict):
        to: 'Address' = params['to']

        value: int = params.get('value', 0)
        if value != 0:
            raise InvalidParamsException('value must be 0 in a deploy transaction')

        if self._is_inactive_score(context, to):
            raise InvalidRequestException(f'{to} is an inactive SCORE')

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise InvalidRequestException('Data not found')

        if 'contentType' not in data:
            raise InvalidRequestException('ContentType not found')

        if 'content' not in data:
            raise InvalidRequestException('Content not found')

        self._validate_new_score_address_on_deploy_transaction(context, params)

    def _validate_deposit_transaction(self, context: 'IconScoreContext', params: dict):
        """Validate deposit transaction

        :param params:
        :return:
        """
        to: 'Address' = params['to']

        if self._is_inactive_score(context, to):
            raise InvalidRequestException(f'{to} is inactive SCORE')

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise InvalidRequestException('Data not found')

        if 'action' not in data:
            raise InvalidRequestException('Action not found')

    @classmethod
    def _validate_new_score_address_on_deploy_transaction(cls, context: 'IconScoreContext', params: dict):
        """Check if a newly generated score address is available
        Assume that data_type is 'deploy'

        :param params:
        :return:
        """

        to: 'Address' = params['to']
        if to != SYSTEM_SCORE_ADDRESS:
            return

        try:
            data: dict = params['data']
            content_type: str = data['contentType']

            if content_type == 'application/zip':
                from_: 'Address' = params['from']
                timestamp: int = params['timestamp']
                nonce: int = params.get('nonce')

                score_address: 'Address' = generate_score_address(from_, timestamp, nonce)

                deploy_info = context.storage.deploy.get_deploy_info(context, score_address)
                if deploy_info is not None:
                    raise InvalidRequestException(f'SCORE address already in use: {score_address}')
            elif content_type == 'application/tbears':
                pass
            else:
                raise InvalidRequestException(f'Invalid contentType: {content_type}')

        except KeyError as ke:
            raise InvalidParamsException(f'Invalid params: {ke}')
        except BaseException as e:
            raise e

    @classmethod
    def _check_balance(cls, context: 'IconScoreContext', from_: 'Address', value: int, fee: int):
        balance = context.engine.icx.get_balance(context, from_)

        if context.revision >= Revision.LOCK_ADDRESS.value and is_address_locked(from_):
            Logger.warning(
                tag="LOCK",
                msg=f"Address is locked: balance={balance} from={from_} value={value} fee={fee}"
            )
            raise InvalidRequestException(f"Address is locked: {from_}")

        if balance < value + fee:
            msg = f"Out of balance: from={from_} balance={balance} value={value} fee={fee}"
            if balance == 0:
                Logger.info(tag=TAG, msg=f"{msg} {context.block}")

            raise OutOfBalanceException(msg)

    def _is_inactive_score(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return (
            address.is_contract
            and address != SYSTEM_SCORE_ADDRESS
            and not self._is_score_active(context, address)
        )

    @classmethod
    def _is_score_active(cls, context: 'IconScoreContext', address: 'Address') -> bool:
        deploy_info: 'IconScoreDeployInfo' = context.storage.deploy.get_deploy_info(context, address)

        if deploy_info is None:
            return False

        return deploy_info.deploy_state == DeployState.ACTIVE
