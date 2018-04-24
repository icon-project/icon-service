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
            "addresses": "address[]"
        }
        _from = f'hx{"0" * 40}'
        _to = f'hx{"1" * 40}'
        _value = 0x1234
        _addresses = ['hx' + str(i) * 40 for i in range(5)]

        converter = TypeConverter(type_table)

        params = {
            "from": str(_from),
            "to": str(_to),
            "value": hex(_value),
            "addresses": _addresses
        }

        ret = converter.convert(params)

        self.assertEqual(_from, ret['from'])
        self.assertEqual(_to, ret['to'])
        self.assertEqual(_value, ret['value'])
        self.assertEqual(_addresses, ret['addresses'])
