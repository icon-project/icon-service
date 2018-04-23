import unittest
from icon.iconservice.base.address import Address
from icon.iconservice.utils.json_util import *


class TestJsonUtils(unittest.TestCase):

    def setUp(self):
        self.one_depth_dict = {"address1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                          "address2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                          "value": "0x12 -> int",
                          "int_val": "1234 -> int",
                          "str_val": "abcdefg -> string"}
        self.two_depth_dict = {"address1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                          "address2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                          "value": "0x1234abcd1234cdef1234abcd1234cdef1234cdef -> int",
                          "int_val": '1234 -> int',
                          "str_val": "abcdefg -> string",
                          "data": {
                                "data-param1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                                "data-param2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef -> address",
                                "data-param3": "0x1234 -> int",
                                "data-param4": '1234 -> int',
                                "data-param5": "abcdefghi -> string",
                                "data-param6": "[hx1234abcd1234cdef1234abcd1234cdef1234cdef, \
                                hx1234abcd1234cdef1234abcd1234cdef1234cdef] -> address_array"
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
        self.assertEqual(str, type(convert_value(self.string + " -> string")))
        self.assertEqual(self.string, convert_value(self.string + " -> string"))

        self.assertEqual(int, type(convert_value(self.value + " -> int")))
        self.assertEqual(int(self.value, 0), convert_value(self.value + " -> int"))

        self.assertEqual(Address, type(convert_value(self.eoa + " -> address")))
        self.assertEqual("hx", convert_value(self.eoa + " -> address").prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef", convert_value(self.eoa + " -> address").body.hex())

        self.assertEqual(Address, type(convert_value(self.ca + " -> address")))
        self.assertEqual("cx", convert_value(self.ca + " -> address").prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef", convert_value(self.ca + " -> address").body.hex())

        self.assertEqual(bool, type(convert_value(self.bool_value + " -> bool")))
        self.assertEqual(True, convert_value(self.bool_value + " -> bool"))

        self.assertEqual(self.int_array, convert_value(self.int_array_str + " -> int_array"))
        self.assertEqual(self.bool_array, convert_value(self.bool_array_str + " -> bool_array"))

        self.assertEqual(self.string_array
                         , convert_value(self.string_array_str + " -> string_array"))

        self.assertTrue(self.address_array[0] == convert_value(self.address_array_str + " -> address_array")[0])
        self.assertTrue(self.address_array[1] == convert_value(self.address_array_str + " -> address_array")[1])

    def test_convert_dict_values(self):
        self.assertEqual(self.one_depth_dict.keys(), convert_dict_values(self.one_depth_dict).keys())
        self.assertEqual(self.two_depth_dict.keys(), convert_dict_values(self.two_depth_dict).keys())
        self.assertEqual(self.two_depth_dict["data"].keys(), convert_dict_values(self.two_depth_dict["data"]).keys())

        self.assertEqual(Address, type(convert_dict_values(self.one_depth_dict)["address1"]))
        self.assertEqual(Address, type(convert_dict_values(self.one_depth_dict)["address2"]))
        self.assertEqual(Address, type(convert_dict_values(self.two_depth_dict["data"])["data-param1"]))

        self.assertEqual(self.eoa, str(convert_dict_values(self.one_depth_dict)['address1']))
        self.assertEqual(self.ca, str(convert_dict_values(self.one_depth_dict)['address2']))

        self.assertEqual(self.eoa, str(convert_dict_values(self.two_depth_dict)['data']['data-param1']))
        self.assertEqual(self.ca, str(convert_dict_values(self.two_depth_dict)['data']['data-param2']))
        self.assertEqual(int(self.value, 0), convert_dict_values(self.one_depth_dict)['value'])


if __name__ == "__main__":
    unittest.main()
