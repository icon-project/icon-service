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

from iconservice import IconScoreBase, IconScoreContextType, IconScoreException
from iconservice.base.address import Address, ICX_ENGINE_ADDRESS
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper, IconScoreInfo
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.icx.icx_storage import IcxStorage

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreInfoMapper(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_db = self._db_factory.create_by_name('test_mapper_dex')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)

        self._icon_score_loader = IconScoreLoader(score_path)
        self.mapper = IconScoreInfoMapper(self._icx_storage, self._db_factory, self._icon_score_loader)
        self.score_address = Address.from_string(f'cx{"0" * 40}')
        self.address = Address.from_string(f'hx{"a" * 40}')

        self.mapper[self.score_address] = IconScoreInfo(
            icon_score=None)

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)

        self._score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self._loader = IconScoreLoader(self._score_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def tearDown(self):
        self._icx_db.close(self._context)
        shutil.rmtree(os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH))
        if os.path.exists(os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)):
            shutil.rmtree(os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH))

    def load_proj(self, proj: str, addr_score: Address) -> IconScoreBase:
        target_path = os.path.join(self._score_path, addr_score.body.hex())
        os.makedirs(target_path, exist_ok=True)
        target_path = os.path.join(target_path, '0_0')

        ref_path = os.path.join(TEST_ROOT_PATH, 'tests/sample/{}'.format(proj))
        os.symlink(ref_path, target_path, target_is_directory=True)
        return self._loader.load_score(addr_score.body.hex())

    def test_setitem(self):
        info = IconScoreInfo(icon_score=None)

        with self.assertRaises(IconScoreException):
            self.mapper[self.address] = None
        with self.assertRaises(IconScoreException):
            self.mapper[self.score_address] = 1

        score_address = Address.from_string(f'cx{"1" * 40}')
        self.mapper[score_address] = info
        self.assertEqual(2, len(self.mapper))

        self.assertIsNone(self.mapper[self.score_address].icon_score)

    def test_getitem(self):

        self.assertEqual(1, len(self.mapper))

        score_address = Address.from_string(f'cx{"0" * 40}')
        score = self.load_proj('test_score01', Address.from_string(f'cx{"0" * 40}'))
        score_info = IconScoreInfo(icon_score=score)

        info = self.mapper[score_address]
        self.assertTrue(isinstance(info, IconScoreInfo))
        # FIXME
        # print('dddd', score_info.address) # -> <property object at ~~>

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


if __name__ == '__main__':
    unittest.main()
