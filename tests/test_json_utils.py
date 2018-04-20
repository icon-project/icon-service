import unittest
from iconservice.base.address import Address
from iconservice.utils.json_util import *


class TestJsonUtils(unittest.TestCase):

    def setUp(self):
        self.one_depth_dict = {"address1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "address2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "value": "0x12",
                          "int_val": 1234,
                          "str_val": "abcdefg"}
        self.two_depth_dict = {"address1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "address2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "value": "0x1234abcd1234cdef1234abcd1234cdef1234cdef",
                          "int_val": 1234,
                          "str_val": "abcdefg",
                          "data": {
                                "data-param1": "hx1234abcd1234cdef1234abcd1234cdef1234cdef",
                                "data-param2": "cx1234abcd1234cdef1234abcd1234cdef1234cdef",
                                "data-param3": "0x1234",
                                "data-param4": 1234,
                                "data-param5": "abcdefghi"
                            }
                          }
        self.eoa = "hx1234abcd1234cdef1234abcd1234cdef1234cdef"
        self.fake_eoa = "hx1234abcd1234cdef1234abcd1234cdef123f"
        self.ca = "cx1234abcd1234cdef1234abcd1234cdef1234cdef"
        self.fake_ca = "cx1234abcd1234cdef1234abcd1f"
        self.value = '0x12'
        self.string = "abcdefg"

    def test_convert_value(self):
        self.assertEqual(str, type(convert_value(self.string)))
        self.assertEqual(self.string, convert_value(self.string))

        self.assertEqual(int, type(convert_value(self.value)))
        self.assertEqual(int(self.value, 0), convert_value(self.value))

        self.assertEqual(Address, type(convert_value(self.eoa)))
        self.assertEqual("hx", convert_value(self.eoa).prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef", convert_value(self.eoa).body.hex())

        self.assertEqual(Address, type(convert_value(self.ca)))
        self.assertEqual("cx", convert_value(self.ca).prefix)
        self.assertEqual("1234abcd1234cdef1234abcd1234cdef1234cdef", convert_value(self.ca).body.hex())

    def test_check_type(self):
        self.assertEqual(CONST_FOR_ADDRESS_CODE, check_type(self.eoa))
        self.assertEqual(CONST_FOR_STR_CODE, check_type(self.fake_eoa))

        self.assertEqual(CONST_FOR_ADDRESS_CODE, check_type(self.ca))
        self.assertEqual(CONST_FOR_STR_CODE, check_type(self.fake_ca))

        self.assertEqual(CONST_FOR_INT_CODE, check_type(self.value))
        self.assertEqual(CONST_FOR_STR_CODE, check_type(0))

        self.assertEqual(CONST_FOR_STR_CODE, check_type(self.string))

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
