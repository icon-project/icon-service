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
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfo
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper, IconScoreInfo


class TestIconScoreInfoMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = IconScoreInfoMapper()
        self.score_address = Address.from_string(f'cx{"0" * 40}')
        self.address = Address.from_string(f'hx{"a" * 40}')

        self.mapper[self.score_address] = IconScoreInfo(
            icon_score=None, owner=self.address)

    def test_setitem(self):
        info = IconScoreInfo(icon_score=None, owner=self.address)

        with self.assertRaises(KeyError):
            self.mapper[self.address] = None
        with self.assertRaises(ValueError):
            self.mapper[self.score_address] = 1

        score_address = Address.from_string(f'cx{"1" * 40}')
        self.mapper[score_address] = info
        self.assertEqual(2, len(self.mapper))

        self.assertIsNone(self.mapper[self.score_address].icon_score)

    def test_getitem(self):
        score_address = Address.from_string(f'cx{"0" * 40}')

        self.assertEqual(1, len(self.mapper))

        info = self.mapper[score_address]
        self.assertTrue(isinstance(info, IconScoreInfo))
        self.assertEqual(score_address, info.address)

    def test_delitem(self):
        score_address = Address.from_string(f'cx{"0" * 40}')

        self.assertEqual(1, len(self.mapper))
        del self.mapper[score_address]
        self.assertEqual(0, len(self.mapper))

    def test_contains(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        self.assertTrue(score_address in self.mapper)

        score_address = Address.from_string(f'cx{"1" * 40}')
        self.assertFalse(score_address in self.mapper)

        score_address = Address.from_string(f'hx{"0" * 40}')
        self.assertFalse(score_address in self.mapper)
