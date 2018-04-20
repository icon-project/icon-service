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


import os
import shutil
import unittest

from iconservice.base.address import Address
from iconservice.database.factory import DatabaseFactory
from iconservice.database.context_db import ReadOnlyContextDatabase 
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfo
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper 


class TestReadOnlyContextDatabase(unittest.TestCase):
    """
    """
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        os.mkdir(state_db_root_path)

        address = Address.from_string(f'cx{"0" * 40}')
        db_factory = DatabaseFactory(state_db_root_path=state_db_root_path)

        mapper = IconScoreInfoMapper()

        IconScoreInfo.set_db_factory(db_factory)
        info = IconScoreInfo(
            icon_score=None,
            owner=None,
            icon_score_address=address)
        mapper[address] = info

        self.state_db = info.db
        self.context_db = ReadOnlyContextDatabase(
            icon_score_address=address,
            icon_score_info_mapper=mapper)

        value = 1
        info.db.put(
            key=Address.from_string(f'hx{"a" * 40}').body,
            value=value.to_bytes(32, 'big'))

    def tearDown(self):
        self.state_db.close()
        try:
            shutil.rmtree(self.state_db_root_path)
        except:
            pass

    def test_get(self):
        """
        """
        address = Address.from_string(f'hx{"a" * 40}')
        value = self.context_db.get(address.body)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(int.from_bytes(value, 'big'), 1)

    def test_put(self):
        """db writting will occur RunTimeError.
        """
        value = 1
        address = Address.from_string(f'hx{"a" * 40}')

        with self.assertRaises(RuntimeError):
            self.context_db.put(address.body, value.to_bytes(32, 'big'))
