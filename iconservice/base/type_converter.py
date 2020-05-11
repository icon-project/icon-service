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

import inspect
from copy import deepcopy
from typing import Union, Any, get_type_hints

from .address import Address, MalformedAddress, is_icon_address_valid
from .exception import InvalidParamsException
from .type_converter_templates import ParamType, \
    type_convert_templates, ValueType, KEY_CONVERTER, CONVERT_USING_SWITCH_KEY, SWITCH_KEY
from ..icon_constant import HASH_TYPE_TABLE
from ..utils import get_main_type_from_annotations_type

score_base_support_type = (int, str, bytes, bool, Address)


class TypeConverter:
    @staticmethod
    def convert(params: Union[list, dict], param_type: ParamType) -> Any:
        if param_type is None:
            return params

        copied_params = deepcopy(params)  # to avoid corrupting original data
        converted_params = TypeConverter._convert(copied_params, type_convert_templates[param_type])
        return converted_params

    @staticmethod
    def _convert(params: Union[str, list, dict, None], template: Union[list, dict, ValueType]) -> Any:
        if TypeConverter._skip_params(params, template):
            return params

        if isinstance(template, dict) and KEY_CONVERTER in template:
            params = TypeConverter._convert_key(params, template[KEY_CONVERTER])

        if isinstance(params, dict) and isinstance(template, dict):
            new_params = {}
            for key, value in params.items():
                if TypeConverter._check_convert_using_method(key, template):
                    ref_key_table = deepcopy(new_params)
                    target_template = TypeConverter._get_convert_using_method_template(key, template)
                    new_value = TypeConverter._convert_using_switch(value, ref_key_table, target_template)
                else:
                    new_value = TypeConverter._convert(value, template.get(key))
                new_params[key] = new_value
        elif isinstance(params, list) and isinstance(template, list):
            new_params = []
            for item in params:
                if isinstance(item, list):
                    new_item = []
                    for element, templete_type in zip(item, template[0]):
                        new_element = TypeConverter._convert(element, templete_type)
                        new_item.append(new_element)
                    new_params.append(new_item)
                else:
                    new_item = TypeConverter._convert(item, template[0])
                    new_params.append(new_item)
        elif isinstance(template, ValueType):
            new_params = TypeConverter._convert_value(params, template)
        else:
            new_params = params

        return new_params

    @staticmethod
    def _convert_key(params, key_convert_dict):
        new_params = {}
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
            raise InvalidParamsException(f'TypeConvert Exception None value, template: {str(template)}')
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
        template_key = tmp_params.get(switch_key)
        target_template = template.get(template_key)

        if isinstance(params, dict) and isinstance(target_template, dict):
            new_params = {}
            for key, value in params.items():
                new_value = TypeConverter._convert(value, target_template.get(key))
                new_params[key] = new_value
        elif isinstance(params, list) and isinstance(target_template, list):
            new_params = []
            for item in params:
                new_item = TypeConverter._convert(item, target_template[0])
                new_params.append(new_item)
        elif isinstance(target_template, ValueType):
            new_params = TypeConverter._convert_value(params, target_template)
        else:
            new_params = params

        return new_params

    @staticmethod
    def _convert_value(value: Any, value_type: ValueType) -> Any:
        if value_type == ValueType.INT:
            converted_value = TypeConverter._convert_value_int(value)
        elif value_type == ValueType.HEXADECIMAL:
            converted_value = TypeConverter._convert_value_hexadecimal(value)
        elif value_type == ValueType.STRING:
            converted_value = TypeConverter._convert_value_string(value)
        elif value_type == ValueType.BOOL:
            converted_value = TypeConverter._convert_value_bool(value)
        elif value_type == ValueType.ADDRESS:
            if len(value) == 0:
                converted_value = None
            else:
                converted_value = TypeConverter._convert_value_address(value)
        elif value_type == ValueType.ADDRESS_OR_MALFORMED_ADDRESS:
            converted_value = TypeConverter._convert_value_address_or_malformed_address(value)
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
    def _convert_value_hexadecimal(value: str) -> int:
        """Convert value into integer, assuming that value is a hexadecimal string

        :param value: hexadecimal string
        :return: int
        """
        if not isinstance(value, str):
            raise InvalidParamsException(
                f'TypeConvert Exception int value :{value}, type: {type(value)}')

        return int(value, 16)

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
    def _convert_value_address_or_malformed_address(value: str) -> 'Address':
        if not isinstance(value, str):
            raise InvalidParamsException(
                f'TypeConvert Exception address value :{value}, type: {type(value)}')

        if is_icon_address_valid(value):
            return Address.from_string(value)

        # This code is just used to support a legacy bug
        # Do not use MalformedAddress elsewhere
        return MalformedAddress.from_string(value)

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
    def get_default_args(func):
        signature = inspect.signature(func)
        return {
            k: v.default
            for k, v in signature.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

    @staticmethod
    def make_annotations_from_method(func: callable) -> dict:
        # in python 3.7, get_type_hints method return _GenericAlias type object
        # (when parameter has 'NoneType' as a default)

        hints = get_type_hints(func)
        if hints.get('return') is not None:
            del hints['return']
        return hints

    @staticmethod
    def convert_data_params(annotations: dict, kw_params: dict) -> None:
        for param_name, param_type in annotations.items():
            if param_name == "self" or param_name == "cls":
                continue

            kw_param = kw_params.get(param_name)
            if kw_param is None:
                continue

            param_type = get_main_type_from_annotations_type(param_type)
            kw_param = TypeConverter._convert_data_value(param_type, kw_param)
            kw_params[param_name] = kw_param

    @staticmethod
    def adjust_params_to_method(func: callable, kw_params: dict, remove_invalid_param: bool = False):
        hints = TypeConverter.make_annotations_from_method(func)
        default_args = TypeConverter.get_default_args(func)

        # check user input argument name is valid
        invalid_keys = []
        for key in kw_params.keys():
            try:
                _type = hints[key]
            except KeyError:
                invalid_keys.append(key)

        if len(invalid_keys) > 0:
            if remove_invalid_param:
                for key in invalid_keys:
                    del kw_params[key]
                if len(kw_params) == 0:
                    # input invalid params only
                    raise InvalidParamsException(f"There is no valid parameters")
            else:
                raise InvalidParamsException(f"Invalid parameters '{invalid_keys}'")

        # check required argument is exist in user input
        for param_name, param_type in hints.items():
            if param_name == "self" or param_name == "cls":
                continue

            try:
                param = kw_params[param_name]
            except KeyError:
                # has no input for this parameter
                try:
                    default_args[param_name]
                except KeyError:
                    # has no default value
                    raise InvalidParamsException(f"There is no '{param_name}' parameter")
                # has default value. pass type converting
                continue

            # all type can have None value
            if param is None:
                continue

            param_type = get_main_type_from_annotations_type(param_type)
            param = TypeConverter._convert_data_value(param_type, param)
            kw_params[param_name] = param

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
                    is_hash = k in HASH_TYPE_TABLE
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
