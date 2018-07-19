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


import inspect
import unittest
from os import path, makedirs, symlink
from typing import TYPE_CHECKING

from iconservice.base.address import AddressPrefix
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.iconscore.icon_score_base import IconScoreBase
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from tests import create_address
from tests.mock_db import create_mock_icon_score_db

if TYPE_CHECKING:
    from iconservice.base.address import Address

TEST_ROOT_PATH = path.abspath(path.join(path.dirname(__file__), '../'))


class TestContextContainer(ContextContainer):
    pass


class MockIconScoreManager(object):
    def get_owner(self, context, address):
        return None


class TestIconScoreLoader(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        self._score_path = path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self._loader = IconScoreLoader(self._score_path)
        self._addr_test_score01 = create_address(AddressPrefix.CONTRACT, b'test_score01')
        self._addr_test_score02 = create_address(AddressPrefix.CONTRACT, b'test_score02')

        self.db = create_mock_icon_score_db()
        self._factory = IconScoreContextFactory(max_size=1)
        IconScoreContext.icon_score_manager = MockIconScoreManager()
        self._context = self._factory.create(IconScoreContextType.DIRECT)
        self._context_container = TestContextContainer()
        self._context_container._put_context(self._context)

    def tearDown(self):
        remove_path = path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        pass

    @staticmethod
    def __ensure_dir(dir_path):
        if not path.exists(dir_path):
            makedirs(dir_path)

    def load_proj(self, proj: str, addr_score: 'Address') -> callable:
        target_path = path.join(self._score_path, addr_score.to_bytes().hex())
        makedirs(target_path, exist_ok=True)
        target_path = path.join(target_path, '0_0')

        ref_path = path.join(TEST_ROOT_PATH, 'tests/sample/{}'.format(proj))
        symlink(ref_path, target_path, target_is_directory=True)
        return self._loader.load_score(addr_score.to_bytes().hex())

    def test_install(self):
        self.__ensure_dir(self._score_path)

        score = self.load_proj('test_score01', self._addr_test_score01)
        print('test_score01', score.get_api())
        score = self.load_proj('test_score02', self._addr_test_score02)
        print('test_score02', score.get_api())

        ins_score = score(self.db)

        ins_score.print_test()
        self.assertTrue(IconScoreBase in inspect.getmro(score))
