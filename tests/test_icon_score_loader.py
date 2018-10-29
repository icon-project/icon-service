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

from unittest.mock import Mock

from iconservice.iconscore.icon_score_base import IconScoreBase
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from tests import create_address, create_tx_hash, rmtree

TEST_ROOT_PATH = path.abspath(path.join(path.dirname(__file__), '../'))


class TestIconScoreLoader(unittest.TestCase):
    _ROOT_SCORE_PATH = '.score'

    def setUp(self):
        self._score_path = self._ROOT_SCORE_PATH
        self._loader = IconScoreLoader(self._score_path)

        self._factory = IconScoreContextFactory(max_size=1)
        IconScoreContext.icon_score_deploy_engine = Mock()
        self._context = self._factory.create(IconScoreContextType.DIRECT)
        ContextContainer._push_context(self._context)

    def tearDown(self):
        ContextContainer._pop_context()
        rmtree(self._score_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not path.exists(dir_path):
            makedirs(dir_path)

    def load_proj(self, proj: str) -> callable:
        addr_score = create_address(1, data=proj.encode())
        target_path = path.join(self._score_path, addr_score.to_bytes().hex())
        makedirs(target_path, exist_ok=True)
        tx_hash = create_tx_hash()
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        target_path = path.join(target_path, converted_tx_hash)

        ref_path = path.join(TEST_ROOT_PATH, 'tests/sample/{}'.format(proj))
        symlink(ref_path, target_path, target_is_directory=True)
        score_path = self._loader.make_score_path(addr_score, tx_hash)
        return self._loader.load_score(score_path)

    def test_install(self):
        self.__ensure_dir(self._score_path)

        score = self.load_proj('test_score01')
        print('test_score01', score.get_api())
        score = self.load_proj('test_score02')
        print('test_score02', score.get_api())

        ins_score = score(Mock())

        ins_score.print_test()
        self.assertTrue(IconScoreBase in inspect.getmro(score))

    def test_make_pkg_root_import(self):
        address = '010cb2b5d7cca1dec18c51de595155a4468711d4f4'
        tx_hash = '0x49485e08589256a68e02a63fa3484b16edd322a729394fbd6b543d77a7f68621'
        score_root_path = './.score'
        score_path = f'{score_root_path}/{address}/{tx_hash}'
        expected_import_name: str = f'{address}.{tx_hash}'

        loader = IconScoreLoader(score_root_path)
        import_name: str = loader._make_pkg_root_import(score_path)
        self.assertEqual(import_name, expected_import_name)

        score_root_path = '/haha/hoho/hehe/score/'
        score_path = f'{score_root_path}/{address}/{tx_hash}'
        loader = IconScoreLoader(score_root_path)
        import_name: str = loader._make_pkg_root_import(score_path)
        self.assertEqual(import_name, expected_import_name)
