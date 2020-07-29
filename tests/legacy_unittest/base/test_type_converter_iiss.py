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

import unittest

from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType, ConstantKeys
from tests import create_address


class TestTypeConverter(unittest.TestCase):

    def test_set_delegation(self):
        address1 = create_address()
        value1 = 1 * 10 ** 18

        address2 = create_address()
        value2 = 2 * 10 ** 18

        request = [
            {
                ConstantKeys.ADDRESS: str(address1),
                ConstantKeys.VALUE: hex(value1)
            },
            {
                ConstantKeys.ADDRESS: str(address2),
                ConstantKeys.VALUE: hex(value2)
            }
        ]

        ret_delegations = TypeConverter.convert(request, ParamType.IISS_SET_DELEGATION)
        self.assertEqual(address1, ret_delegations[0][ConstantKeys.ADDRESS], f'{type(ret_delegations[0][ConstantKeys.ADDRESS])}')
        self.assertEqual(value1, ret_delegations[0][ConstantKeys.VALUE])
        self.assertEqual(address2, ret_delegations[1][ConstantKeys.ADDRESS])
        self.assertEqual(value2, ret_delegations[1][ConstantKeys.VALUE])
