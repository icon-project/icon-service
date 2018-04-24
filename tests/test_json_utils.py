import unittest
from icon.iconservice.base.address import Address
from icon.iconservice.utils.json_util import *


class TestJsonUtils(unittest.TestCase):

    def setUp(self):
        self.type_table_dict = {
            "from": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
            "to": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
            "value": "0x12",
            "values": "[1,2,3,4,5,6,'10', '0x12']",
            "signature": "sssssig",
            "addresses": "['hx1234abcd1234cdef1234abcd1234cdef1234cdef', hx1234abcd1234cdef1234abcd1234cdef1234cdee']",
            "success": "True",
            "boolList" :"[True, False, 'True', 'False']",
            "stringList": "['asdf', 'zxcv', 'qwer']"
        }
        self.two_depth_dict = {"address1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "address2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "value": "0x1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "int_val": '1234',
                          "str_val": "abcdefg",
                          "data": {
                                "data-param1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
                                "data-param2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
                                "data-param3": "0x1234",
                                "data-param4": '1234',
                                "data-param5": "abcdefghi",
                                "data-param6": "[hx1234abcd1234cdef1234abcd1234cdef1234cdef, \
                                hx1234abcd1234cdef1234abcd1234cdef1234cdef]"
                            }
                          }
        self.type_info = {
            "type_table": {
                "from": "address",
                "to": "address",
                "value": "int",
                "values": "int[]",
                "signature": "string",
                "addresses": "address[]",
                "success": "bool",
                "boolList": "bool[]",
                "stringList": "string[]"
                # "balances": "dict[address:int]"
                },
            "two_depth_json_type": {
                "address1": "address",
                "address2": "address",
                "value": "int",
                "int_val": 'int',
                "str_val": "string",
                "data": {
                    "data-param1": "address",
                    "data-param2": "address",
                    "data-param3": "int",
                    "data-param4": 'int',
                    "data-param5": "string",
                    "data-param6": "address[]"
                }
            }
        }

        self.eoa = "hx1234abcd1234cdef1234abcd1234cdef1234cdef"
        self.ca = "cx1234abcd1234cdef1234abcd1234cdef1234cdef"
        self.value = '0x12'
        self.string = "abcdefg"
        self.bool_value = "True"

        self.int_array_str = "['1', '2', '3', '0x12', '4']"
        self.int_array = [1, 2, 3, 0x12, 4]
        self.string_array_str = "['123', '123', 'asdf', 'qwer']"
        self.string_array = ['123', '123', 'asdf', 'qwer']
        self.bool_array_str = "['True', 'False', 'True', 'False']"
        self.bool_array = [True, False, True, False]
        self.address_array_str = "['hx1234abcd1234cdef1234abcd1234cdef1234cdef',\
        'hx1234abcd1234cdef1234abcd1234cdef1234cdee']"
        self.address_array = [Address('hx', bytes.fromhex('1234abcd1234cdef1234abcd1234cdef1234cdef')),
                              Address('hx', bytes.fromhex('1234abcd1234cdef1234abcd1234cdef1234cdee'))]

    def test_convert_value(self):
        self.assertEqual(str, type(convert_value(self.string, "type_table", "signature")))
        self.assertEqual(self.string, convert_value(self.string, "type_table", "signature"))

        self.assertEqual(int, type(convert_value(self.value, "type_table", "value")))
        self.assertEqual(int(self.value, 0), convert_value(self.value, "type_table", "value"))

        self.assertEqual(Address, type(convert_value(self.eoa, "type_table", "from")))
        self.assertEqual("hx", convert_value(self.eoa, "type_table", "from").prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef"
                         , convert_value(self.eoa, "type_table", "from").body.hex())

        self.assertEqual(Address, type(convert_value(self.ca, "type_table", "to")))
        self.assertEqual("cx", convert_value(self.ca, "type_table", "to").prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef"
                         , convert_value(self.ca, "type_table", "to").body.hex())

        self.assertEqual(bool, type(convert_value(self.bool_value, "type_table", "success")))
        self.assertEqual(True, convert_value(self.bool_value, "type_table", "success"))

        self.assertEqual(self.int_array, convert_value(self.int_array_str, "type_table", "values"))
        self.assertEqual(self.bool_array, convert_value(self.bool_array_str, "type_table", "boolList"))

        self.assertEqual(self.string_array
                         , convert_value(self.string_array_str, "type_table", "stringList"))

        self.assertTrue(self.address_array[0] == convert_value(self.address_array_str, "type_table", "addresses")[0])
        self.assertTrue(self.address_array[1] == convert_value(self.address_array_str, "type_table", "addresses")[1])

    def test_convert_dict_values(self):
        self.assertEqual(self.type_table_dict.keys(), convert_dict_values(self.type_table_dict, "type_table").keys())
        self.assertEqual(self.two_depth_dict.keys()
                         , convert_dict_values(self.two_depth_dict, "two_depth_json_type").keys())
        self.assertEqual(self.two_depth_dict["data"].keys(),
                         convert_dict_values(self.two_depth_dict["data"], "two_depth_json_type", "data").keys())

        self.assertEqual(Address, type(convert_dict_values(self.type_table_dict, "type_table")["from"]))
        self.assertEqual(Address, type(convert_dict_values(self.type_table_dict, "type_table")["to"]))
        self.assertEqual(Address
                         , type(convert_dict_values(self.two_depth_dict, "two_depth_json_type")["data"]["data-param1"]))

        self.assertEqual(self.eoa, str(convert_dict_values(self.type_table_dict, "type_table")['from']))
        self.assertEqual(self.ca, str(convert_dict_values(self.type_table_dict, "type_table")['to']))

        self.assertEqual(self.eoa
                         , str(convert_dict_values(self.two_depth_dict, "two_depth_json_type")['data']['data-param1']))
        self.assertEqual(self.ca
                         , str(convert_dict_values(self.two_depth_dict, "two_depth_json_type")['data']['data-param2']))
        self.assertEqual(int(self.value, 0)
                         , convert_dict_values(self.type_table_dict, "type_table")['value'])


if __name__ == "__main__":
    unittest.main()
