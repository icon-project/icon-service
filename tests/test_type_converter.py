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

from iconservice.base.type_converter import TypeConverter
from iconservice.base.address import Address


class TestTypeConverter(unittest.TestCase):
    def setUp(self):
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
            "data": "bytes",
            "balance": "int",
            "address": "address"
        }
        self.converter = TypeConverter(type_table)

    def tearDown(self):
        self.converter = None

    def test_convert(self):
        converter = self.converter

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
        _data = bytes.fromhex("0x1232"[2:])

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
                "data": "0x1232"
            },
            "unknown": _unknown
        }

        ret = converter.convert(params, recursive=True)

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

    def test_convert_recursively(self):
        input = {
            "transaction_data": {
                "accounts": [
                    {
                        "name": "god",
                        "address": "hx0000000000000000000000000000000000000000",
                        "balance": "0x2961ffa20dd47f5c4700000"
                    },
                    {
                        "name": "treasury",
                        "address": "hx1000000000000000000000000000000000000000",
                        "balance": "0x0"
                    }
                ],
                "message": "A rHizomE has no beGInning Or enD; it is alWays IN the miDDle, between tHings, interbeing, intermeZzO. ThE tree is fiLiatioN, but the rhizome is alliance, uniquelY alliance. The tree imposes the verb \"to be\" but the fabric of the rhizome is the conJUNction, \"AnD ... and ...and...\"THis conJunction carriEs enouGh force to shaKe and uproot the verb \"to be.\" Where are You goIng? Where are you coMing from? What are you heading for? These are totally useless questions.\n\n- 『Mille Plateaux』, Gilles Deleuze & Felix Guattari\n\n\"Hyperconnect the world\""
            }
        }

        converter = self.converter
        output = converter.convert(input, recursive=True)

        accounts = output['transaction_data']['accounts']
        self.assertTrue(isinstance(accounts, list))

        for account in accounts:
            name = account['name']
            address = account['address']
            balance = account['balance']

            self.assertTrue(isinstance(name, str))
            self.assertTrue(isinstance(address, Address))
            self.assertTrue(isinstance(balance, int))

        input2 = {
            "transaction_data": {
                "accounts": [
                    {
                        "name": "god",
                        "address": "hx0000000000000000000000000000000000000000",
                        "balance": "0x2961ffa20dd47f5c4700000"
                    },
                    {
                        "name": "treasury",
                        "address": "hx1000000000000000000000000000000000000000",
                        "balance": "0x0"
                    }
                ],
                "message": "A rHizomE has no beGInning Or enD; it is alWays IN the miDDle, between tHings, interbeing, intermeZzO. ThE tree is fiLiatioN, but the rhizome is alliance, uniquelY alliance. The tree imposes the verb \"to be\" but the fabric of the rhizome is the conJUNction, \"AnD ... and ...and...\"THis conJunction carriEs enouGh force to shaKe and uproot the verb \"to be.\" Where are You goIng? Where are you coMing from? What are you heading for? These are totally useless questions.\n\n- 『Mille Plateaux』, Gilles Deleuze & Felix Guattari\n\n\"Hyperconnect the world\""
            }
        }
        output2 = converter.convert(input2, recursive=False)

        accounts2 = output2['transaction_data']['accounts']
        self.assertTrue(isinstance(accounts2, list))

        for account in accounts2:
            name = account['name']
            address = account['address']
            balance = account['balance']

            self.assertTrue(isinstance(name, str))
            self.assertFalse(isinstance(address, Address))
            self.assertFalse(isinstance(balance, int))

    def test_convert_list_values(self):
        input = [
            {
                "name": "god",
                "address": "hx0000000000000000000000000000000000000000",
                "balance": "0x2961ffa20dd47f5c4700000"
            },
            {
                "name": "treasury",
                "address": "hx1000000000000000000000000000000000000000",
                "balance": "0x0"
            }
        ]

        converter = self.converter
        output = converter.convert_list_values(input, False)

        self.assertTrue(isinstance(output, list))

        account = output[0]
        name = account['name']
        address = account['address']
        balance = account['balance']

        self.assertTrue(isinstance(name, str))
        self.assertEqual('god', name)
        self.assertTrue(isinstance(address, Address))
        self.assertEqual("hx0000000000000000000000000000000000000000", str(address))
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0x2961ffa20dd47f5c4700000, balance)

        account = output[1]
        name = account['name']
        address = account['address']
        balance = account['balance']

        self.assertTrue(isinstance(name, str))
        self.assertEqual('treasury', name)
        self.assertTrue(isinstance(address, Address))
        self.assertEqual("hx1000000000000000000000000000000000000000", str(address))
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0, balance)

        input2 = [
            {
                "name": "god",
                "address": "hx0000000000000000000000000000000000000000",
                "balance": "0x2961ffa20dd47f5c4700000",
                "data-field": {
                    "name": "god",
                    "address": "hx0000000000000000000000000000000000000000"
                }
            },
            {
                "name": "treasury",
                "address": "hx1000000000000000000000000000000000000000",
                "balance": "0x0"
            }
        ]

        output2 = converter.convert(input2, recursive=False)

        account1 = output2[0]
        account2 = output2[1]

        self.assertEqual(account1["name"], "god")
        self.assertTrue(isinstance(account1['address'], Address))
        self.assertTrue(isinstance(account1['balance'], int))

        self.assertFalse(isinstance(account1['data-field']['address'], Address))
