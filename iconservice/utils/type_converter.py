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

import copy

from ..base.address import Address


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

    def convert(self, params: object, recursive: bool) -> dict:
        if isinstance(params, dict):
            return self.convert_dict_values(params, recursive)
        elif isinstance(params, list):
            return self.convert_list_values(params, recursive)

        return params

    def convert_dict_values(self, input: dict, recursive: bool) -> dict:
        """Convert json into appropriate format.

        Original input is preserved after convert is done.

        :param input:
        :return:
        """
        output = {}

        for key, value in input.items():
            if isinstance(value, dict):
                if recursive:
                    output[key] = self.convert_dict_values(value,
                                                           recursive)
                else:
                    output[key] = copy.deepcopy(value)
            else:
                output[key] = self.convert_value(key, value)

        return output

    def convert_list_values(self, input: list, recursive: bool) -> list:
        output = []

        for item in input:
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
            value_type = self.type_table[key]

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
