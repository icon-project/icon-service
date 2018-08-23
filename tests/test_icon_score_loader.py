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

import inspect
import unittest
from os import path, makedirs, symlink
from time import sleep

from typing import TYPE_CHECKING

from iconservice.base.address import AddressPrefix
from iconservice.iconscore.icon_score_base import IconScoreBase
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from tests import create_address, create_tx_hash, rmtree, TEST_ROOT_PATH
from tests.mock_db import create_mock_icon_score_db

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestContextContainer(ContextContainer):
    pass


class MockIconScoreManager(object):
    def get_owner(self, context, address):
        return None


class TestIconScoreLoader(unittest.TestCase):
    _ROOT_SCORE_PATH = '.score'
    _TEST_DB_PATH = './statedb'

    def setUp(self):
        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

        self._loader = IconScoreLoader(self._ROOT_SCORE_PATH)

        self.db = create_mock_icon_score_db()
        self.factory = IconScoreContextFactory(max_size=1)
        IconScoreContext.icon_score_manager = MockIconScoreManager()
        self._context = self.factory.create(IconScoreContextType.DIRECT)
        self._context_container = TestContextContainer()
        self._context_container._push_context(self._context)

    def tearDown(self):
        self.engine = None
        self._context.type = IconScoreContextType.DIRECT
        self.factory.destroy(self._context)

        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

    @staticmethod
    def __ensure_dir(dir_path):
        if not path.exists(dir_path):
            makedirs(dir_path)

    def load_proj(self, proj: str, addr_score: 'Address') -> callable:
        target_path = path.join(self._ROOT_SCORE_PATH, addr_score.to_bytes().hex())
        makedirs(target_path, exist_ok=True)
        tx_hash = create_tx_hash()
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        target_path = path.join(target_path, converted_tx_hash)

        ref_path = path.join(TEST_ROOT_PATH, 'sample/{}'.format(proj))
        symlink(ref_path, target_path, target_is_directory=True)
        return self._loader.load_score(addr_score.to_bytes().hex(), tx_hash)

    def test_install(self):
        self.__ensure_dir(self._ROOT_SCORE_PATH)
        sleep(1)
        score = self.load_proj('test_score01', create_address(AddressPrefix.CONTRACT))
        print('test_score01', score.get_api())
        sleep(1)
        score = self.load_proj('test_score02', create_address(AddressPrefix.CONTRACT))
        print('test_score02', score.get_api())

        ins_score = score(self.db)

        ins_score.print_test()
        self.assertTrue(IconScoreBase in inspect.getmro(score))
