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


import unittest

from iconservice.base.address import Address, AddressPrefix
from iconservice.utils.type_converter import TypeConverter


class TestTypeConverter(unittest.TestCase):
    def test_convert(self):
        type_table = {
            "from": "address",
            "to": "address",
            "value": "int",
            "addresses": "address[]",
            "bool": "bool",
            "bool2": "bool",
            "bool_array": "bool[]",
            "int_array": "int[]",
            "str_array1": "string[]",
            "str_array2": "string[]",
            "data": "bytes"
        }

        _from = f'hx{"0" * 40}'
        _to = f'hx{"1" * 40}'
        _value = 0x1234
        _addresses = ['hx' + str(i) * 40 for i in range(5)]
        _bool = True
        _bool2 = False
        _bool_array = [True, False, True, False]
        _int_array = [0x1, 0x2, 0x3, 0x1234, 0x5]
        _str_array1 = ["asdf", 'qwer', 'qwer', 'zxcv']
        _unknown = "asdf"
        converter = TypeConverter(type_table)
        _data = b'1234'

        params = {
            "from": str(_from),
            "to": str(_to),
            "value": hex(_value),
            "addresses": _addresses,
            "int_array": _int_array,
            "bool": "True",
            "bool2": "False",
            "bool_array": _bool_array,
            "str_array1": _str_array1,
            "data": {
                "value": "0x1234",
                "data": _data.decode('utf-8')
            },
            "unknown": _unknown
        }

        ret = converter.convert(params)

        self.assertEqual(_from, str(ret['from']))
        self.assertEqual(_to, str(ret['to']))

        self.assertEqual(_bool, ret['bool'])
        self.assertEqual(_bool2, ret['bool2'])

        self.assertEqual(_value, ret['value'])

        self.assertEqual(_bool_array, ret['bool_array'])
        self.assertEqual(_int_array, ret['int_array'])
        self.assertEqual(_str_array1, ret['str_array1'])

        self.assertEqual(_addresses[0], str(ret['addresses'][0]))
        self.assertEqual(_addresses[1], str(ret['addresses'][1]))
        self.assertEqual(_addresses[2], str(ret['addresses'][2]))
        self.assertEqual(_addresses[3], str(ret['addresses'][3]))
        self.assertEqual(_addresses[4], str(ret['addresses'][4]))

        self.assertEqual(_value, ret['data']['value'])
        self.assertEqual(_data, ret['data']['data'])

        self.assertEqual(_unknown, ret['unknown'])
