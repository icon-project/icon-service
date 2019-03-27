#!/usr/bin/env python3
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
from iconservice.base.msgpack_util import MsgPackConverter, TypeTag
from tests import create_address


class TestMsgpackUtil(unittest.TestCase):

    def test_msgpack_util_loads_dumps(self):
        expected_struct: list = [1, -1,
                                 b'123456', b'',
                                 [1, 2, 3, 4, 5],
                                 {1: 2, 3: 4},
                                 True, False,
                                 None]

        data: bytes = MsgPackConverter.dumps(expected_struct)
        struct: list = MsgPackConverter.loads(data)
        self.assertEqual(expected_struct, struct)

    def test_masgpack_util_encode_deoode(self):
        expected_struct: list = [1, -1,
                                 b'123456', b'',
                                 "hello", "",
                                 create_address(),
                                 None]

        data_list: list = []
        for value in expected_struct:
            data_list.append(MsgPackConverter.encode(value))

        data: bytes = MsgPackConverter.dumps(data_list)
        struct: list = MsgPackConverter.loads(data)

        actual_struct: list = [
            MsgPackConverter.decode(TypeTag.INT, struct[0]),
            MsgPackConverter.decode(TypeTag.INT, struct[1]),
            MsgPackConverter.decode(TypeTag.BYTES, struct[2]),
            MsgPackConverter.decode(TypeTag.BYTES, struct[3]),
            MsgPackConverter.decode(TypeTag.STRING, struct[4]),
            MsgPackConverter.decode(TypeTag.STRING, struct[5]),
            MsgPackConverter.decode(TypeTag.ADDRESS, struct[6]),
            MsgPackConverter.decode(TypeTag.NIL, struct[7])]

        self.assertEqual(expected_struct, actual_struct)

    def test_masgpack_util_optional_encode_deoode(self):
        expected_struct: list = [None, 1,
                                 None, b'hello',
                                 None, "hello",
                                 None, create_address()]

        data_list: list = []
        for value in expected_struct:
            data_list.append(MsgPackConverter.optional_encode(value))

        data: bytes = MsgPackConverter.dumps(data_list)
        struct: list = MsgPackConverter.loads(data)

        actual_struct: list = [
            MsgPackConverter.optional_decode(TypeTag.INT, struct[0]),
            MsgPackConverter.optional_decode(TypeTag.INT, struct[1]),
            MsgPackConverter.optional_decode(TypeTag.BYTES, struct[2]),
            MsgPackConverter.optional_decode(TypeTag.BYTES, struct[3]),
            MsgPackConverter.optional_decode(TypeTag.STRING, struct[4]),
            MsgPackConverter.optional_decode(TypeTag.STRING, struct[5]),
            MsgPackConverter.optional_decode(TypeTag.ADDRESS, struct[6]),
            MsgPackConverter.optional_decode(TypeTag.ADDRESS, struct[7])]

        self.assertEqual(expected_struct, actual_struct)


if __name__ == '__main__':
    unittest.main()
