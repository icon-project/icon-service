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
import os
import sys
import unittest
from unittest.mock import Mock

from iconservice.deploy import DeployEngine, DeployStorage
from iconservice.deploy.utils import convert_path_to_package_name
from iconservice.iconscore.icon_score_base import IconScoreBase
from iconservice.iconscore.icon_score_class_loader import IconScoreClassLoader
from iconservice.iconscore.icon_score_constant import ATTR_SCORE_GET_API
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.utils import ContextEngine, ContextStorage
from tests import create_address, create_tx_hash, rmtree

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreClassLoader(unittest.TestCase):
    _SCORE_ROOT_PATH = '.score'

    def setUp(self):
        self._score_root_path = self._SCORE_ROOT_PATH
        sys.path.append(self._score_root_path)

        IconScoreContext.engine = ContextEngine(
            icx=None,
            deploy=Mock(spec=DeployEngine),
            fee=None,
            iiss=None,
            prep=None,
            issue=None
        )
        IconScoreContext.storage = ContextStorage(
            icx=None,
            deploy=Mock(spec=DeployStorage),
            fee=None,
            iiss=None,
            prep=None,
            issue=None,
            rc=None,
            meta=None
        )

        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        ContextContainer._push_context(self._context)

    def tearDown(self):
        ContextContainer._pop_context()
        rmtree(self._score_root_path)
        sys.path.remove(self._score_root_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def load_proj(self, proj: str) -> callable:
        score_address = create_address(1, data=proj.encode())
        score_path = os.path.join(self._score_root_path, score_address.to_bytes().hex())
        os.makedirs(score_path, exist_ok=True)

        tx_hash: bytes = create_tx_hash()
        score_deploy_path: str = os.path.join(score_path, f'0x{tx_hash.hex()}')

        ref_path = os.path.join(TEST_ROOT_PATH, 'tests/sample/{}'.format(proj))
        os.symlink(ref_path, score_deploy_path, target_is_directory=True)
        return IconScoreClassLoader.run(score_address, tx_hash, self._SCORE_ROOT_PATH)

    def test_install(self):
        self.__ensure_dir(self._score_root_path)

        score = self.load_proj('test_score01')

        get_api = getattr(score, ATTR_SCORE_GET_API)
        print('test_score01', get_api())
        score = self.load_proj('test_score02')
        get_api = getattr(score, ATTR_SCORE_GET_API)
        print('test_score02', get_api())

        ins_score = score(Mock())

        ins_score.print_test()
        self.assertTrue(IconScoreBase in inspect.getmro(score))

    def test_make_pkg_root_import(self):
        address = '010cb2b5d7cca1dec18c51de595155a4468711d4f4'
        tx_hash = '0x49485e08589256a68e02a63fa3484b16edd322a729394fbd6b543d77a7f68621'
        score_root_path = './.score'
        score_path = f'{score_root_path}/{address}/{tx_hash}'
        expected_import_name: str = f'{address}.{tx_hash}'
        index: int = len(score_root_path)

        import_name: str = convert_path_to_package_name(score_path[index:])
        self.assertEqual(import_name, expected_import_name)

        score_root_path = '/haha/hoho/hehe/score/'
        index: int = len(score_root_path)
        score_path = f'{score_root_path}/{address}/{tx_hash}'
        import_name: str = convert_path_to_package_name(score_path[index:])
        self.assertEqual(import_name, expected_import_name)

    def test_get_package_info_0(self):
        package_json = {
            'version': '1.0.0',
            'main_module': 'token',
            'main_score': 'Token'
        }

        main_module, main_score = IconScoreClassLoader._get_package_info(package_json)
        self.assertEqual('token', main_module)
        self.assertEqual('Token', main_score)

    def test_get_package_info_1(self):
        package_json = {
            'version': '1.0.0',
            'main_file': 'token',
            'main_score': 'Token'
        }

        main_module, main_score = IconScoreClassLoader._get_package_info(package_json)
        self.assertEqual('token', main_module)
        self.assertEqual('Token', main_score)

    def test_get_package_info_2(self):
        package_json = {
            'version': '1.0.0',
            'main_file': 'invalid.token',
            'main_module': 'valid.token',
            'main_score': 'Token'
        }

        main_module, main_score = IconScoreClassLoader._get_package_info(package_json)
        self.assertEqual('valid.token', main_module)
        self.assertEqual('Token', main_score)
