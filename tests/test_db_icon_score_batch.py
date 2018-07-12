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

from iconservice.base.address import Address, AddressPrefix
from iconservice.database.batch import IconScoreBatch
from tests import create_address


class TestIconScoreBatch(unittest.TestCase):
    def setUp(self):

        self.addr1 = create_address(AddressPrefix.EOA, b'addr1')
        self.addr2 = create_address(AddressPrefix.EOA, b'addr2')
        self.addr3 = create_address(AddressPrefix.EOA, b'addr3')

        self.icon_score_batch = IconScoreBatch(self.addr1)
        self.icon_score_batch[self.addr2] = 100
        self.icon_score_batch[self.addr3] = 200

    def tearDown(self):
        self.icon_score_batch = None

    def test_address_property(self):
        self.assertEqual(self.addr1, self.icon_score_batch.address)

    def test_get_item(self):
        self.assertEqual(100, self.icon_score_batch[self.addr2])
        self.assertEqual(200, self.icon_score_batch[self.addr3])

    def test_len(self):
        self.assertEqual(2, len(self.icon_score_batch))

    def test_put_item(self):
        icon_score_batch = IconScoreBatch(self.addr1)
        address = create_address(AddressPrefix.EOA, b'addr4')
        icon_score_batch[address] = 300
        self.assertEqual(300, icon_score_batch[address])

    def test_iter(self):
        i = 0
        for key in self.icon_score_batch:
            self.assertTrue(isinstance(key, Address))
            self.assertEqual(AddressPrefix.EOA, key.prefix)
            i += 1

        self.assertEqual(len(self.icon_score_batch), i)
