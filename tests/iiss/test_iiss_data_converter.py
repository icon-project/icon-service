# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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
from typing import TYPE_CHECKING

from iconservice.base.exception import InvalidParamsException

from tests import create_address
from iconservice.iiss.iiss_data_converter import IissCodec, TypeTag, IissDataConverter

if TYPE_CHECKING:
    pass


class TestIissDataConverter(unittest.TestCase):
    def test_iiss_codec_eoa_address(self):
        codec: 'IissCodec' = IissCodec()

        eoa_addr = create_address()
        tag, data = codec.encode(eoa_addr)
        ret_addr = codec.decode(tag, data)
        self.assertEqual(TypeTag.ADDRESS, tag)
        self.assertEqual(eoa_addr, ret_addr)

    def test_iiss_codec_eoa_address_raise_exception(self):
        codec: 'IissCodec' = IissCodec()

        with self.assertRaises(InvalidParamsException) as cm:
            addr = "invalid address"
            codec.encode(addr)
            tag, data = codec.encode(addr)
            codec.decode(tag, data)
        self.assertEqual(cm.exception.message, f"Invalid encode type: {type(addr)}")

        with self.assertRaises(InvalidParamsException) as cm:
            addr = create_address()
            tag, data = codec.encode(addr)
            wrong_type = TypeTag.STRING
            codec.decode(wrong_type, data)
        self.assertEqual(cm.exception.message, f"UnknownType: {type(wrong_type)}")

    def test_iiss_codec_score_address(self):
        codec: 'IissCodec' = IissCodec()

        score_addr = create_address(1)
        tag, data = codec.encode(score_addr)
        ret_addr = codec.decode(tag, data)
        self.assertEqual(TypeTag.ADDRESS, tag)
        self.assertEqual(score_addr, ret_addr)

    def test_iiss_data_converter_encode_decode_int(self):
        int_value: int = 10
        data: bytes = IissDataConverter.encode(int_value)
        ret_int: int = IissDataConverter.decode(TypeTag.INT, data)
        self.assertEqual(int_value, ret_int)

    def test_iiss_data_converter_encode_decode_str(self):
        str_value: str = "str_value"
        data: bytes = IissDataConverter.encode(str_value)
        ret_str: str = IissDataConverter.decode(TypeTag.STRING, data)
        self.assertEqual(str_value, ret_str)

    def test_iiss_data_converter_encode_decode_bytes(self):
        bytes_value: bytes = b'byte_value'
        data: bytes = IissDataConverter.encode(bytes_value)
        ret_bytes: bytes = IissDataConverter.decode(TypeTag.BYTES, data)
        self.assertEqual(bytes_value, ret_bytes)

    def test_iiss_data_converter_encode_decode_bool(self):
        bool_value: bool = True
        data: bytes = IissDataConverter.encode(bool_value)
        ret_bool: bool = bool(IissDataConverter.decode(TypeTag.INT, data))
        self.assertEqual(bool_value, ret_bool)

    def test_iiss_data_converter_encode_decode_none(self):
        none_value = None
        data: bytes = IissDataConverter.encode(none_value)
        ret_none = IissDataConverter.decode(TypeTag.NIL, data)
        self.assertEqual(none_value, ret_none)

    def test_iiss_data_converter_encode_decode_none_raise_exception(self):
        with self.assertRaises(InvalidParamsException) as cm:
            none_value = "wrong_data"
            data: bytes = IissDataConverter.encode(none_value)
            IissDataConverter.decode(TypeTag.NIL, data)
        self.assertEqual(cm.exception.message, f"Invalid tag type:{TypeTag.NIL} value: {data}")

    def test_iiss_data_converter_encode_decode_any_int(self):
        int_value: int = 10
        data: tuple = IissDataConverter.encode_any(int_value)
        ret_int = IissDataConverter.decode_any(data)
        self.assertEqual(int_value, ret_int)

    def test_iiss_data_converter_encode_decode_any_str(self):
        str_value: str = "str_value"
        data: tuple = IissDataConverter.encode_any(str_value)
        ret_str = IissDataConverter.decode_any(data)
        self.assertEqual(str_value, ret_str)

    def test_iiss_data_converter_encode_decode_any_str(self):
        str_value: str = "str_value"
        data: tuple = IissDataConverter.encode_any(str_value)
        ret_str = IissDataConverter.decode_any(data)
        self.assertEqual(str_value, ret_str)

    def test_iiss_data_converter_encode_decode_any_byte(self):
        bytes_value: str = b"byte_value"
        data: tuple = IissDataConverter.encode_any(bytes_value)
        ret_bytes = IissDataConverter.decode_any(data)
        self.assertEqual(bytes_value, ret_bytes)

    def test_iiss_data_converter_encode_decode_any_none(self):
        none_value = None
        data: tuple = IissDataConverter.encode_any(none_value)
        ret_none = IissDataConverter.decode_any(data)
        self.assertEqual(none_value, ret_none)

    def test_iiss_data_converter_encode_decode_any_list(self):
        list_value: list = [1,2,[3,4,[5,6]]]
        data: tuple = IissDataConverter.encode_any(list_value)
        ret_list = IissDataConverter.decode_any(data)
        self.assertEqual(list_value, ret_list)

    def test_iiss_data_converter_encode_decode_any_dict(self):
        dict_value: dict = {"a": 1, "b": 2, "c": {"d": 3}}
        data: tuple = IissDataConverter.encode_any(dict_value)
        ret_dict = IissDataConverter.decode_any(data)
        self.assertEqual(dict_value, ret_dict)


if __name__ == '__main__':
    unittest.main()
