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

from copy import deepcopy
from typing import Union, Any, get_type_hints
from enum import IntEnum

from .address import Address
from .exception import InvalidParamsException

score_base_support_type = (int, str, bytes, bool, Address)


class ParamType(IntEnum):
    BLOCK = 0

    INVOKE_TRANSACTION = 100
    ACCOUNT_DATA = 101
    CALL_DATA = 102
    DEPLOY_DATA = 103

    INVOKE = 200

    QUERY = 300
    ICX_CALL = 301
    ICX_GET_BALANCE = 302
    ICX_GET_TOTAL_SUPPLY = 303
    ICX_GET_SCORE_API = 304
    ISE_GET_STATUS = 305

    WRITE_PRECOMMIT = 400
    REMOVE_PRECOMMIT = 500

    VALIDATE_TRANSACTION = 600


class ValueType(IntEnum):
    IGNORE = 0
    LATER = 1
    INT = 2
    STRING = 3
    BOOL = 4
    ADDRESS = 5
    BYTES = 6


type_convert_templates = dict()
CONVERT_USING_SWITCH_KEY = 'CONVERT_USING_SWITCH_KEY'
SWITCH_KEY = "SWITCH_KEY"
KEY_CONVERTER = 'KEY_CONVERTER'


class TypeConverter:
    @staticmethod
    def convert(params: dict, param_type: ParamType) -> Any:
        if param_type is None:
            return params

        copied_params = deepcopy(params)  # to avoid corrupting original data
        converted_params = TypeConverter._convert(copied_params, type_convert_templates[param_type])
        return converted_params

    @staticmethod
    def _convert(params: Union[str, dict, None], template: Union[list, dict, ValueType]) -> Any:
        if TypeConverter._skip_params(params, template):
            return params

        if isinstance(template, dict) and KEY_CONVERTER in template:
            params = TypeConverter._convert_key(params, template[KEY_CONVERTER])

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
    def _convert_key(params, key_convert_dict):
        new_params = dict()
        for key in params:
            if key in key_convert_dict:
                old_key = key
                new_key = key_convert_dict[old_key]
                new_params[new_key] = params[old_key]
            else:
                new_params[key] = params[key]

        return new_params

    @staticmethod
    def _check_convert_using_method(param: str, template: dict) -> bool:
        params = template.get(param)
        if isinstance(params, dict):
            return CONVERT_USING_SWITCH_KEY in params
        return False

    @staticmethod
    def _get_convert_using_method_template(key: str, template: dict) -> dict:
        tmp_params = template.get(key)
        return tmp_params.get(CONVERT_USING_SWITCH_KEY)

    @staticmethod
    def _skip_params(params: Union[str, dict, None], template: Union[list, dict, ValueType]) -> bool:
        if params is None:
            raise InvalidParamsException(f'TypeConvert Exception None value, templete: {str(template)}')
        if isinstance(params, str):
            if params != "" and not template:
                return True
        elif not params or not template:
            return True
        return False
    
    @staticmethod
    def _convert_using_switch(params: Union[str, dict, None],
                              tmp_params: dict,
                              template: Union[list, dict, ValueType]) -> Any:
        if TypeConverter._skip_params(params, template):
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
            if value.startswith('0x') or value.startswith('-0x'):
                return int(value, 16)
            else:
                return int(value)
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
            if value.startswith('0x'):
                return bytes.fromhex(value[2:])
            else:
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

            param = TypeConverter._filter_none_type(param)
            kw_param = TypeConverter._convert_data_value(param, kw_param)
            kw_params[key] = kw_param

    @staticmethod
    def _filter_none_type(annotation_type: type) -> type:
        main_type = None
        if hasattr(annotation_type, '_subs_tree'):
            # Generic type has a '_subs_tree'
            sub_tree = annotation_type._subs_tree()
            if isinstance(sub_tree, tuple):
                for t in sub_tree:
                    if t is Union or t is type(None):
                        pass
                    else:
                        main_type = t
                        break
            else:
                # Generic declaration only
                main_type = sub_tree
        else:
            main_type = annotation_type
        return main_type

    @staticmethod
    def _convert_data_value(annotation_type: type, param: Any) -> Any:
        if annotation_type == int:
            param = TypeConverter._convert_value_int(param)
        elif annotation_type == str:
            param = TypeConverter._convert_value_string(param)
        elif annotation_type == bool:
            param = TypeConverter._convert_value_bool(param)
        elif annotation_type == Address:
            param = TypeConverter._convert_value_address(param)
        elif annotation_type == bytes:
            param = TypeConverter._convert_value_bytes(param)
        return param

    @staticmethod
    def convert_type_reverse(value: Any):
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, bytes):
                    is_hash = k in ('blockHash', 'txHash', 'prevBlockHash')
                    value[k] = TypeConverter._convert_bytes_reverse(v, is_hash)
                else:
                    value[k] = TypeConverter.convert_type_reverse(v)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = TypeConverter.convert_type_reverse(v)
        elif isinstance(value, int):
            value = hex(value)
        elif isinstance(value, Address):
            value = str(value)
        elif isinstance(value, bytes):
            value = TypeConverter._convert_bytes_reverse(value)
        return value

    @staticmethod
    def _convert_bytes_reverse(value: bytes, is_hash: bool = False):
        if is_hash:
            # if the value is of 'txHash' or 'blockHash', excludes '0x' prefix
            return bytes.hex(value)
        else:
            return f'0x{bytes.hex(value)}'


type_convert_templates[ParamType.BLOCK] = {
    "blockHeight": ValueType.INT,
    "blockHash": ValueType.BYTES,
    "timestamp": ValueType.INT,
    "prevBlockHash": ValueType.BYTES,
}

type_convert_templates[ParamType.ACCOUNT_DATA] = {
    "name": ValueType.STRING,
    "address": ValueType.ADDRESS,
    "balance": ValueType.INT
}

type_convert_templates[ParamType.CALL_DATA] = {
    "method": ValueType.STRING,
    "params": ValueType.LATER
}

type_convert_templates[ParamType.DEPLOY_DATA] = {
    "contentType": ValueType.STRING,
    "content": ValueType.IGNORE,
    "params": ValueType.LATER
}

type_convert_templates[ParamType.INVOKE_TRANSACTION] = {
    "method": ValueType.STRING,
    "params": {
        "txHash": ValueType.BYTES,
        "version": ValueType.INT,
        "from": ValueType.ADDRESS,
        "to": ValueType.ADDRESS,
        "value": ValueType.INT,
        "stepLimit": ValueType.INT,
        "fee": ValueType.INT,
        "timestamp": ValueType.INT,
        "nonce": ValueType.INT,
        "signature": ValueType.IGNORE,
        "dataType": ValueType.STRING,
        "data": {
            CONVERT_USING_SWITCH_KEY: {
                SWITCH_KEY: "dataType",
                "call": type_convert_templates[ParamType.CALL_DATA],
                "deploy": type_convert_templates[ParamType.DEPLOY_DATA]
            }
        },
        KEY_CONVERTER: {
            "tx_hash": "txHash"
        }
    },
    "genesisData": {
        "accounts": [
            type_convert_templates[ParamType.ACCOUNT_DATA]
        ],
        "message": ValueType.STRING
    }
}

type_convert_templates[ParamType.INVOKE] = {
    "block": type_convert_templates[ParamType.BLOCK],
    "transactions": [
        type_convert_templates[ParamType.INVOKE_TRANSACTION]
    ]
}

type_convert_templates[ParamType.ICX_CALL] = {
    "version": ValueType.INT,
    "from": ValueType.ADDRESS,
    "to": ValueType.ADDRESS,
    "dataType": ValueType.STRING,
    "data": ValueType.LATER
}
type_convert_templates[ParamType.ICX_GET_BALANCE] = {
    "version": ValueType.INT,
    "address": ValueType.ADDRESS
}
type_convert_templates[ParamType.ICX_GET_TOTAL_SUPPLY] = {
    "version": ValueType.INT
}
type_convert_templates[ParamType.ICX_GET_SCORE_API] = type_convert_templates[ParamType.ICX_GET_BALANCE]

type_convert_templates[ParamType.ISE_GET_STATUS] = {
    "filter": [ValueType.STRING]
}

type_convert_templates[ParamType.QUERY] = {
    "method": ValueType.STRING,
    "params": {
        CONVERT_USING_SWITCH_KEY: {
            SWITCH_KEY: "method",
            "icx_call": type_convert_templates[ParamType.ICX_CALL],
            "icx_getBalance": type_convert_templates[ParamType.ICX_GET_BALANCE],
            "icx_getTotalSupply": type_convert_templates[ParamType.ICX_GET_TOTAL_SUPPLY],
            "icx_getScoreApi": type_convert_templates[ParamType.ICX_GET_SCORE_API],
            "ise_getStatus": type_convert_templates[ParamType.ISE_GET_STATUS]
        }
    }
}

type_convert_templates[ParamType.WRITE_PRECOMMIT] = {
    "blockHeight": ValueType.INT,
    "blockHash": ValueType.BYTES
}
type_convert_templates[ParamType.REMOVE_PRECOMMIT] = type_convert_templates[ParamType.WRITE_PRECOMMIT]

type_convert_templates[ParamType.VALIDATE_TRANSACTION] = {
    "method": ValueType.STRING,
    "params": {
        "version": ValueType.INT,
        "txHash": ValueType.BYTES,
        "from": ValueType.ADDRESS,
        "to": ValueType.ADDRESS,
        "value": ValueType.INT,
        "stepLimit": ValueType.INT,
        "fee": ValueType.INT,
        "timestamp": ValueType.INT,
        "nonce": ValueType.INT,
        "signature": ValueType.IGNORE,
        "dataType": ValueType.STRING,
        "data": {
            CONVERT_USING_SWITCH_KEY: {
                SWITCH_KEY: "dataType",
                "call": type_convert_templates[ParamType.CALL_DATA],
                "deploy": type_convert_templates[ParamType.DEPLOY_DATA]
            }
        },
        KEY_CONVERTER: {
            "tx_hash": "txHash"
        }
    }
}
