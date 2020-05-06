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
from typing import Any

from iconservice.base.address import Address, SYSTEM_SCORE_ADDRESS
from iconservice.utils.msgpack_for_db import MsgPackForDB
from iconservice.utils.msgpack_for_ipc import MsgPackForIpc, TypeTag
from tests import create_address


debug = False


class TestMsgpackForIpc(unittest.TestCase):
    def test_msgpack_loads_dumps(self):
        expected_struct: list = [
            1,
            -1,
            b"123456",
            b"",
            [1, 2, 3, 4, 5],
            {1: 2, 3: 4},
            True,
            False,
            None,
        ]

        data: bytes = MsgPackForIpc.dumps(expected_struct)
        struct: list = MsgPackForIpc.loads(data)
        self.assertEqual(expected_struct, struct)

    def test_msgpack_for_ipc_encode_deoode(self):
        expected_struct: list = [
            1,
            -1,
            b"123456",
            b"",
            "hello",
            "",
            create_address(),
            None,
        ]

        data_list: list = []
        for value in expected_struct:
            data_list.append(MsgPackForIpc.encode(value))

        data: bytes = MsgPackForIpc.dumps(data_list)
        struct: list = MsgPackForIpc.loads(data)

        actual_struct: list = [
            MsgPackForIpc.decode(TypeTag.INT, struct[0]),
            MsgPackForIpc.decode(TypeTag.INT, struct[1]),
            MsgPackForIpc.decode(TypeTag.BYTES, struct[2]),
            MsgPackForIpc.decode(TypeTag.BYTES, struct[3]),
            MsgPackForIpc.decode(TypeTag.STRING, struct[4]),
            MsgPackForIpc.decode(TypeTag.STRING, struct[5]),
            MsgPackForIpc.decode(TypeTag.ADDRESS, struct[6]),
            MsgPackForIpc.decode(TypeTag.NIL, struct[7]),
        ]

        self.assertEqual(expected_struct, actual_struct)

    def test_length_check(self):
        int_table = [-1, 0, 1, 10 ** 30]
        bytes_table = [b"hello", b"", SYSTEM_SCORE_ADDRESS.to_bytes()]
        str_table = ["hello", ""]
        address_table = [create_address(), create_address(1)]
        dict_table = {"1": 1, "2": 2, "3": 3}
        list_table = [1, 2, 3, 4, 5]
        bool_table = [True, False]

        if debug:
            expected_struct: list = [
                int_table,
                bytes_table,
                str_table,
                address_table,
                dict_table,
                list_table,
                bool_table,
            ]
            self._prt_length_info("all", expected_struct)

            expected_struct: list = [int_table]
            self._prt_length_info("int", expected_struct)

            expected_struct: list = [bytes_table]
            self._prt_length_info("bytes", expected_struct)

            expected_struct: list = [str_table]
            self._prt_length_info("str", expected_struct)

            expected_struct: list = [address_table]
            self._prt_length_info("addr", expected_struct)

            expected_struct: list = [dict_table]
            self._prt_length_info("dict", expected_struct)

            expected_struct: list = [list_table]
            self._prt_length_info("list", expected_struct)

            expected_struct: list = [bool_table]
            self._prt_length_info("bool", expected_struct)

            expected_struct: list = [SYSTEM_SCORE_ADDRESS]
            self._prt_length_info("zero_addr", expected_struct)

            expected_struct: list = b"hello"
            self._prt_length_info("hello_bin", expected_struct)
            expected_struct: list = b""
            self._prt_length_info("empty_bin", expected_struct)
            expected_struct: list = SYSTEM_SCORE_ADDRESS.to_bytes()
            self._prt_length_info("addr_bin", expected_struct)

    def _prt_length_info(self, tag: str, data: list):
        new_expected_struct: list = self._encode_msg(data)
        data: bytes = MsgPackForIpc.dumps(new_expected_struct)

        print(f"{tag} data: {new_expected_struct}")
        print(f"{tag} length: {len(data)}")

    def _encode_msg(self, obj: Any):

        if isinstance(obj, (int, bytes, str, Address, bool)):
            return MsgPackForIpc.encode(obj)
        elif isinstance(obj, list):
            tmp: list = []
            for i in obj:
                tmp.append(self._encode_msg(i))
            return tmp
        elif isinstance(obj, dict):
            tmp: dict = {}
            for k, v in obj.items():
                tmp[self._encode_msg(k)] = self._encode_msg(v)
            return tmp


class TestMsgpackForStateDB(unittest.TestCase):
    def test_msgpack_for_db_loads_dumps(self):
        int_table = [-1, 0, 1, 10 ** 30]
        bytes_table = [b"hello", b"", SYSTEM_SCORE_ADDRESS.to_bytes()]
        str_table = ["hello", ""]
        address_table = [create_address(), create_address(1)]
        dict_table = {"1": 1, "2": 2, "3": 3}
        list_table = [1, 2, 3, 4, 5]
        bool_table = [True, False]
        None_table = [None]

        expected_struct: list = [
            int_table,
            bytes_table,
            str_table,
            address_table,
            dict_table,
            list_table,
            bool_table,
            None_table,
        ]

        data: bytes = MsgPackForDB.dumps(expected_struct)
        struct: list = MsgPackForDB.loads(data)
        self.assertEqual(expected_struct, struct)

    def test_msgpack_for_db_length(self):
        int_table = [-1, 0, 1, 10 ** 30]
        bytes_table = [b"hello", b"", SYSTEM_SCORE_ADDRESS.to_bytes()]
        str_table = ["hello", ""]
        address_table = [create_address(), create_address(1)]
        dict_table = {"1": 1, "2": 2, "3": 3}
        list_table = [1, 2, 3, 4, 5]
        bool_table = [True, False]

        if debug:
            expected_struct: list = [
                int_table,
                bytes_table,
                str_table,
                address_table,
                dict_table,
                list_table,
                bool_table,
            ]
            self._prt_length_info("all", expected_struct)

            expected_struct: list = [int_table]
            self._prt_length_info("int", expected_struct)

            expected_struct: list = [bytes_table]
            self._prt_length_info("bytes", expected_struct)

            expected_struct: list = [str_table]
            self._prt_length_info("str", expected_struct)

            expected_struct: list = [address_table]
            self._prt_length_info("addr", expected_struct)

            expected_struct: list = [dict_table]
            self._prt_length_info("dict", expected_struct)

            expected_struct: list = [list_table]
            self._prt_length_info("list", expected_struct)

            expected_struct: list = [bool_table]
            self._prt_length_info("bool", expected_struct)

            expected_struct: list = [SYSTEM_SCORE_ADDRESS]
            self._prt_length_info("zero_addr", expected_struct)

            expected_struct: list = b"hello"
            self._prt_length_info("hello_bin", expected_struct)
            expected_struct: list = b""
            self._prt_length_info("empty_bin", expected_struct)
            expected_struct: list = SYSTEM_SCORE_ADDRESS.to_bytes()
            self._prt_length_info("addr_bin", expected_struct)

    def _prt_length_info(self, tag: str, data_list: list):
        data: bytes = MsgPackForDB.dumps(data_list)
        print(f"{tag} data: {data_list}")
        print(f"{tag} length: {len(data)}")


if __name__ == "__main__":
    unittest.main()
