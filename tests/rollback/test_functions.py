# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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
from iconservice.rollback import get_backup_filename


class TestFunctions(unittest.TestCase):
    def test_get_backup_filename(self):
        heights = [0, 1, 123456789, 1234567890]
        expected_filenames = [
            "block-0000000000.bak",
            "block-0000000001.bak",
            "block-0123456789.bak",
            "block-1234567890.bak",
        ]

        for i in range(len(heights)):
            filename: str = get_backup_filename(heights[i])
            assert filename == expected_filenames[i]
