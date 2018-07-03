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

from copy import deepcopy
from typing import Union, Any, get_type_hints
from enum import IntEnum

from .address import Address
from .exception import InvalidParamsException

score_base_support_type = (int, str, bytes, bool, Address)


class ParamType(IntEnum):
    block = 0
    transaction = 1

    invoke_call = 2
    invoke_deploy = 3

    invoke = 4
    query = 5

    icx_call = 6
    icx_get_balance = 7
    icx_get_total_supply = 8
    icx_get_score_api = 9

    write_precommit = 10
    remove_precommit = 11

    validate_transaction = 12
    account_data = 13
    genesis_data = 14


class ValueType(IntEnum):
    IGNORE = 0
    LATER = 1
    INT = 2
    STRING = 3
    BOOL = 4
    ADDRESS = 5
    BYTES = 6


type_convert_templates = dict()
CONVERT_USING_METHOD = 'CONVERT_USING_METHOD'
SWITCH_KEY = "SWITCH_KEY"


class TypeConverter:
    @staticmethod
    def convert(params: dict, param_type: ParamType) -> Any:
        if param_type is None:
            return params

        copied_params = deepcopy(params)  # to avoid corrupting original data
        converted_params = TypeConverter._convert(copied_params, type_convert_templates[param_type])
        return converted_params

    @staticmethod
    def _convert(params: dict, template: Union[list, dict]) -> Any:
        if not params or not template:
            return params

        if isinstance(params, dict) and isinstance(template, dict):
            new_params = dict()
            for key, value in params.items():
                if TypeConverter._check_convert_using_method(key, template):
                    ref_key_table = deepcopy(new_params)
                    target_template = TypeConverter._get_convert_using_method_template(key, template)
                    new_value = TypeConverter._convert_using_switch(value, ref_key_table, target_template)
                else:
                    new_value = TypeConverter._convert(value, template.get(key))
                new_params[key] = new_value
        elif isinstance(params, list) and isinstance(template, list):
            new_params = list()
            for item in params:
                new_item = TypeConverter._convert(item, template[0])
                new_params.append(new_item)
        elif isinstance(template, ValueType):
            new_params = TypeConverter._convert_value(params, template)
        else:
            new_params = params

        return new_params

    @staticmethod
    def _check_convert_using_method(param: str, template: dict) -> bool:
        params = template.get(param)
        if isinstance(params, dict):
            return CONVERT_USING_METHOD in params
        return False

    @staticmethod
    def _get_convert_using_method_template(key: str, template: dict) -> dict:
        tmp_params = template.get(key)
        return tmp_params.get(CONVERT_USING_METHOD)

    @staticmethod
    def _convert_using_switch(params: dict, tmp_params: dict, template: Union[list, dict]) -> Any:
        if not params or not template:
            return params

        switch_key = template.get(SWITCH_KEY)
        templete_key = tmp_params.get(switch_key)
        target_templete = template.get(templete_key)

        if isinstance(params, dict) and isinstance(target_templete, dict):
            new_params = dict()
            for key, value in params.items():
                new_value = TypeConverter._convert(value, target_templete.get(key))
                new_params[key] = new_value
        elif isinstance(params, list) and isinstance(target_templete, list):
            new_params = list()
            for item in params:
                new_item = TypeConverter._convert(item, target_templete[0])
                new_params.append(new_item)
        elif isinstance(target_templete, ValueType):
            new_params = TypeConverter._convert_value(params, target_templete)
        else:
            new_params = params

        return new_params

    @staticmethod
    def _convert_value(value: Any, value_type: ValueType) -> Any:
        if value_type == ValueType.INT:
            converted_value = TypeConverter._convert_value_int(value)
        elif value_type == ValueType.STRING:
            converted_value = TypeConverter._convert_value_string(value)
        elif value_type == ValueType.BOOL:
            converted_value = TypeConverter._convert_value_bool(value)
        elif value_type == ValueType.ADDRESS:
            converted_value = TypeConverter._convert_value_address(value)
        elif value_type == ValueType.BYTES:  # hash...(block_hash, tx_hash)
            converted_value = TypeConverter._convert_value_bytes(value)
        else:
            converted_value = value
        return converted_value

    @staticmethod
    def _convert_value_int(value: str) -> int:
        if isinstance(value, str):
            return int(value, 16)
        else:
            raise InvalidParamsException(f'TypeConvert Exception int value :{value}, type: {type(value)}')

    @staticmethod
    def _convert_value_string(value: str) -> str:
        if isinstance(value, str):
            return value
        else:
            raise InvalidParamsException(f'TypeConvert Exception str value :{value}, type: {type(value)}')

    @staticmethod
    def _convert_value_bool(value: str) -> bool:
        if isinstance(value, str):
            return bool(TypeConverter._convert_value_int(value))
        else:
            raise InvalidParamsException(f'TypeConvert Exception bool value :{value}, type: {type(value)}')

    @staticmethod
    def _convert_value_address(value: str) -> 'Address':
        if isinstance(value, str):
            return Address.from_string(value)
        else:
            raise InvalidParamsException(f'TypeConvert Exception address value :{value}, type: {type(value)}')

    @staticmethod
    def _convert_value_bytes(value: str) -> bytes:
        if isinstance(value, str):
            return bytes.fromhex(value)
        else:
            raise InvalidParamsException(f'TypeConvert Exception bytes value :{value}, type: {type(value)}')

    @staticmethod
    def make_annotations_from_method(func: callable) -> dict:
        hints = get_type_hints(func)
        if hints.get('return') is not None:
            del hints['return']
        return hints

    @staticmethod
    def convert_data_params(annotation_params: dict, kw_params: dict) -> None:

        for key, param in annotation_params.items():
            if key == 'self' or key == 'cls':
                continue

            kw_param = kw_params.get(key)
            if kw_param is None:
                continue

            kw_param = TypeConverter._convert_data_value(param, kw_param)
            kw_params[key] = kw_param

    @staticmethod
    def _convert_data_value(annotation_type: type, param: Any) -> Any:
        if annotation_type == int:
            param = TypeConverter._convert_value_int(param)
        elif annotation_type == bool:
            param = TypeConverter._convert_value_bool(param)
        elif annotation_type == Address:
            param = TypeConverter._convert_value_address(param)
        elif annotation_type == bytes:
            param = TypeConverter._convert_value_bytes(param)
        return param


type_convert_templates[ParamType.block] = {
    "blockHeight": ValueType.INT,
    "blockHash": ValueType.BYTES,
    "timestamp": ValueType.INT,
    "prevBlockHash": ValueType.BYTES,
}
type_convert_templates[ParamType.transaction] = {
    "method": ValueType.STRING,
    "params": {
        "txHash": ValueType.BYTES,
        "version": ValueType.INT,
        "from": ValueType.ADDRESS,
        "to": ValueType.ADDRESS,
        "value": ValueType.INT,
        "stepLimit": ValueType.INT,
        "timestamp": ValueType.INT,
        "nonce": ValueType.INT,
        "signature": ValueType.IGNORE,
        "dataType": ValueType.STRING,
        "data": ValueType.LATER
    },
    "genesisData": ValueType.LATER
}

type_convert_templates[ParamType.invoke] = {
    "block": type_convert_templates[ParamType.block],
    "transactions": [
        type_convert_templates[ParamType.transaction]
    ]
}

type_convert_templates[ParamType.icx_call] = {
    "version": ValueType.INT,
    "from": ValueType.ADDRESS,
    "to": ValueType.ADDRESS,
    "dataType": ValueType.STRING,
    "data": ValueType.LATER
}
type_convert_templates[ParamType.icx_get_balance] = {
    "version": ValueType.INT,
    "address": ValueType.ADDRESS
}
type_convert_templates[ParamType.icx_get_total_supply] = {
    "version": ValueType.INT
}
type_convert_templates[ParamType.icx_get_score_api] = type_convert_templates[ParamType.icx_get_balance]

type_convert_templates[ParamType.query] = {
    "method": ValueType.STRING,
    "params": {
        CONVERT_USING_METHOD: {
            SWITCH_KEY: "method",
            "icx_call": type_convert_templates[ParamType.icx_call],
            "icx_getBalance": type_convert_templates[ParamType.icx_get_balance],
            "icx_getTotalSupply": type_convert_templates[ParamType.icx_get_total_supply],
            "icx_getScoreApi": type_convert_templates[ParamType.icx_get_score_api],
        }
    }
}

type_convert_templates[ParamType.write_precommit] = {
    "blockHeight": ValueType.INT,
    "blockHash": ValueType.BYTES
}
type_convert_templates[ParamType.remove_precommit] = type_convert_templates[ParamType.write_precommit]

type_convert_templates[ParamType.validate_transaction] = type_convert_templates[ParamType.transaction]

type_convert_templates[ParamType.account_data] = {
    "name": ValueType.STRING,
    "address": ValueType.ADDRESS,
    "balance": ValueType.INT
}

type_convert_templates[ParamType.genesis_data] = {
    "accounts": [
        type_convert_templates[ParamType.account_data]
    ],
    "message": ValueType.STRING
}
