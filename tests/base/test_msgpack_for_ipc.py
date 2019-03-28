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
from iconservice.base.msgpack.msgpack_for_ipc import MsgPackForIpc, TypeTag
from tests import create_address


class TestMsgpackForIpc(unittest.TestCase):

    def test_msgpack_loads_dumps(self):
        expected_struct: list = [1, -1,
                                 b'123456', b'',
                                 [1, 2, 3, 4, 5],
                                 {1: 2, 3: 4},
                                 True, False,
                                 None]

        data: bytes = MsgPackForIpc.dumps(expected_struct)
        struct: list = MsgPackForIpc.loads(data)
        self.assertEqual(expected_struct, struct)

    def test_msgpack_for_ipc_encode_deoode(self):
        expected_struct: list = [1, -1,
                                 b'123456', b'',
                                 "hello", "",
                                 create_address(),
                                 None]

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
            MsgPackForIpc.decode(TypeTag.NIL, struct[7])]

        self.assertEqual(expected_struct, actual_struct)


if __name__ == '__main__':
    unittest.main()
