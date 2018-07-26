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

from iconservice.utils import is_lowercase_hex_string


class TestUtils(unittest.TestCase):
    def test_is_lowercase_hex_string(self):
        # if prefix is present, return false.
        a = '0x00678792645ed9f18f1560c4b2e1b0aa028f61e4'
        ret = is_lowercase_hex_string(a)
        self.assertFalse(ret)

        ret = is_lowercase_hex_string(a[2:])
        self.assertTrue(ret)

        # empty string is not hexdecimal.
        self.assertFalse(is_lowercase_hex_string(''))

        a = '72917492AF'
        self.assertFalse(is_lowercase_hex_string(a))


if __name__ == '__main__':
    unittest.main()
