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
        self.param_type_table = type_table

    def convert(self, params: dict) -> dict:
        return self.convert_dict_values(params)

    def convert_dict_values(self, json_dict: dict) -> dict:
        """Convert json into appropriate format.

        :param json_dict:
        :return:
        """
        json_dictionary = {}

        for key in json_dict:
            if isinstance(json_dict[key], dict):
                json_dictionary[key] = self.convert_dict_values(json_dict[key])
            else:
                json_dictionary[key] = self.convert_value(key, json_dict[key])

        return json_dictionary

    def convert_value(self, key, value):
        """Convert str value into specified type.

        :param key:
        :param value:
        :return:
        """
        try:
            value_type = self.param_type_table[key]
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
            else:
                return value
        except KeyError:
            return value
