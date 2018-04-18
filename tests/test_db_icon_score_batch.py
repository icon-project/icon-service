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

from iconservice.base.address import Address
from iconservice.database.icon_score_batch import IconScoreBatch


class TestIconScoreBatch(unittest.TestCase):
    def setUp(self):
        self.address = Address.from_string(f'cx{"0" * 40}')
        self.icon_score_batch = IconScoreBatch(self.address)

        address = Address.from_string(f'hx{"1" * 40}')
        self.icon_score_batch[address] = 100

        address = Address.from_string(f'hx{"2" * 40}')
        self.icon_score_batch[address] = 200

    def tearDown(self):
        self.icon_score_batch = None

    def test_address(self):
        address = Address.from_string(f'hx{"0" * 40}')
        self.assertEqual(address, self.icon_score_batch.address)

    def test_get_item(self):
        pass
