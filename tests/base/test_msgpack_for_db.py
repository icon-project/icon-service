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
from iconservice.base.msgpack.msgpack_for_db import MsgPackForDB
from tests import create_address


class TestMsgpackForStateDB(unittest.TestCase):

    def test_msgpack_for_db_loads_dumps(self):
        int_table = [-1, 0, 1]
        bytes_table = [b'hello', b'', create_address().to_bytes()]
        str_table = ["hello", ""]
        address_table = [create_address(), create_address(1)]
        dict_table = {"1": 1, "2": 2, "3": 3}
        list_table = [1,2,3,4,5]
        bool_table = [True, False]
        None_table = [None]

        expected_struct: list = [
            int_table, bytes_table, str_table, address_table,
            dict_table, list_table, bool_table, None_table
        ]

        data: bytes = MsgPackForDB.dumps(expected_struct)
        struct: list = MsgPackForDB.loads(data)
        self.assertEqual(expected_struct, struct)


if __name__ == '__main__':
    unittest.main()
