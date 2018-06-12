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
from typing import Any, get_type_hints
from ..base.address import Address
from .utils import int_to_bytes


class TypeConverter(object):

    CONST_INT = "int"
    CONST_STRING = "string"
    CONST_BOOL = "bool"
    CONST_ADDRESS = "address"
    CONST_INT_ARRAY = "int[]"
    CONST_STRING_ARRAY = "string[]"
    CONST_BOOL_ARRAY = "bool[]"
    CONST_ADDRESS_ARRAY = "address[]"
    CONST_BYTES = "bytes"

    def __init__(self, type_table: dict=None) -> None:
        self.type_table = type_table

    def convert(self, params: Any, recursive: bool) -> Any:
        if isinstance(params, dict):
            return self.convert_dict_values(params, recursive)
        elif isinstance(params, list):
            return self.convert_list_values(params, recursive)
        return params

    def convert_dict_values(self, input_params: dict, recursive: bool) -> dict:
        """Convert json into appropriate format.

        Original input is preserved after convert is done.

        :param input_params:
        :param recursive:
        :return:
        """
        output = {}

        for key, value in input_params.items():
            if isinstance(value, dict):
                if recursive:
                    output[key] = self.convert_dict_values(value, recursive)
                else:
                    output[key] = deepcopy(value)
            elif isinstance(value, list):
                if recursive:
                    output[key] = self.convert_list_values(value, recursive)
                else:
                    output[key] = deepcopy(value)
            else:
                output[key] = self.convert_value(key, value)

        return output

    def convert_list_values(self, input_params: list, recursive: bool) -> list:
        output = []

        for item in input_params:
            if isinstance(item, dict):
                item = self.convert_dict_values(item, recursive)
            if isinstance(item, list) and recursive:
                item = self.convert_list_values(item, recursive)

            output.append(item)

        return output

    def convert_value(self, key: str, value: object) -> object:
        """Convert str value into the type specified in _type_table

        :param key:
        :param value:
        :return:
        """
        try:
            if not isinstance(value, str):
                return value

            value_type = self.type_table.get(key)

            if value_type == TypeConverter.CONST_INT:
                return int(str(value), 0)
            elif value_type == TypeConverter.CONST_BOOL:
                return value == "True" or value is True
            elif value_type == TypeConverter.CONST_ADDRESS:
                return Address.from_string(value)
            elif value_type == TypeConverter.CONST_ADDRESS_ARRAY:
                return [Address.from_string(a) for a in value]
            elif value_type == TypeConverter.CONST_BYTES:
                return bytes.fromhex(value[2:])
        except KeyError:
            if isinstance(value, list):
                return self.convert_list_values(value, recursive=True)
        except:
            pass

        return value

    @staticmethod
    def make_annotations_from_method(func: callable):
        hints = get_type_hints(func)
        if hints.get('return') is not None:
            del hints['return']
        return hints

    @staticmethod
    def convert_params(annotation_params: dict, kw_params: dict) -> None:

        for key, param in annotation_params.items():
            if key == 'self' or key == 'cls':
                continue

            kw_param = kw_params.get(key)
            if kw_param is None:
                continue

            kw_param = TypeConverter.__convert_value(param, kw_param)
            kw_params[key] = kw_param

    @staticmethod
    def __convert_value(annotation_type: type, param: Any):
        if annotation_type == int:
            param = int(str(param), 0)
        elif annotation_type == bool:
            param = param == "True" or param is True
        elif annotation_type == Address:
            if isinstance(param, Address):
                param = param
            else:
                param = Address.from_string(param)
        elif annotation_type == bytes:
            if isinstance(param, int):
                param = int_to_bytes(param)
            elif isinstance(param, str):
                param = param.encode()
            elif isinstance(param, bool):
                param = int(param)
                param = int_to_bytes(param)
            elif isinstance(param, Address):
                byte_array = bytearray(param.body)
                byte_array.append(param.prefix)
                param = bytes(byte_array)
        return param
