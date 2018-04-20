#!/usr/bin/env python3
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

from iconservice.icx.icx_error import Code, IcxError


class TestCode(unittest.TestCase):
    def test_code(self):
        self.assertTrue(Code.OK == 0)
        self.assertTrue(str(Code.OK) == 'Ok')

        self.assertTrue(Code.INVALID_REQUEST == -32600)
        self.assertTrue(str(Code.INVALID_REQUEST) == 'Invalid Request')

        self.assertTrue(Code.METHOD_NOT_FOUND == -32601)
        self.assertTrue(str(Code.METHOD_NOT_FOUND) == 'Method not found')

        self.assertTrue(Code.INVALID_PARAMS == -32602)
        self.assertTrue(str(Code.INVALID_PARAMS) == 'Invalid params')

        self.assertTrue(Code.INTERNAL_ERROR == -32603)
        self.assertTrue(str(Code.INTERNAL_ERROR) == 'Internal error')

        self.assertTrue(Code.PARSE_ERROR == -32700)
        self.assertTrue(str(Code.PARSE_ERROR) == 'Parse error')


class TestIcxError(unittest.TestCase):
    def test_code_with_default_message(self):
        for code in list(Code):
            try:
                raise IcxError(code)
            except IcxError as icxe:
                self.assertTrue(icxe.code == code)
                self.assertTrue(icxe.message == str(code))

    def test_code_with_custom_message(self):
        for code in list(Code):
            try:
                raise IcxError(code, 'hello')
            except IcxError as icxe:
                self.assertTrue(icxe.code == code)
                self.assertTrue(icxe.message == 'hello')


if __name__ == '__main__':
    unittest.main()
