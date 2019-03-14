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

"""IconScoreEngine testcase
"""


import os
import unittest
from unittest import mock

from iconservice.base.address import AddressPrefix
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, InvalidParamsException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.deploy.utils import remove_path
from iconservice.iconscore.icon_score_class_loader import IconScoreClassLoader
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.icx.icx_storage import IcxStorage
from tests import create_tx_hash, create_block_hash
from tests import rmtree, create_address

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreEngine(unittest.TestCase):
    _SCORE_ROOT_PATH = os.path.join(TEST_ROOT_PATH, 'score')
    _TEST_DB_PATH = 'tests/test_db/'

    def setUp(self):
        rmtree(self._SCORE_ROOT_PATH)
        rmtree(self._TEST_DB_PATH)

        archive_path = 'tests/sample/normal_score.zip'
        archive_path = os.path.join(TEST_ROOT_PATH, archive_path)
        zip_bytes = self.read_zipfile_as_byte(archive_path)
        install_path = os.path.join(TEST_ROOT_PATH, self._SCORE_ROOT_PATH)
        self.__unpack_zip_file(install_path, zip_bytes)

        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        ContextDatabaseFactory.open(
            db_path, ContextDatabaseFactory.Mode.SINGLE_DB)

        self.__ensure_dir(db_path)

        icx_db = ContextDatabaseFactory.create_by_name('icx_db')
        self.icx_storage = IcxStorage(icx_db)
        deploy_storage = IconScoreDeployStorage(self.icx_storage.db)
        deploy_engine = IconScoreDeployEngine()
        deploy_engine.open(deploy_storage)

        IconScoreClassLoader.init(self._SCORE_ROOT_PATH)

        IconScoreMapper.deploy_storage = deploy_storage
        self.icon_score_mapper = IconScoreMapper()

        self.engine = IconScoreEngine()
        # Use mock to prevent an exception from IconScoreEngine._validate_score_blacklist().
        IconScoreEngine._validate_score_blacklist = mock.Mock()

        self._from = create_address(AddressPrefix.EOA)
        self._icon_score_address = create_address(AddressPrefix.CONTRACT)

        IconScoreContext.icon_score_deploy_engine = deploy_engine
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.msg = Message(self._from, 0)
        tx_hash = create_tx_hash()
        self._context.tx = Transaction(
            tx_hash, origin=create_address(AddressPrefix.EOA))
        block_hash = create_block_hash()
        self._context.block = Block(1, block_hash, 0, None)

    def tearDown(self):
        self.engine = None
        self.icx_storage.close(self._context)
        ContextDatabaseFactory.close()

        path = os.path.join(TEST_ROOT_PATH, self._SCORE_ROOT_PATH)
        remove_path(path)
        path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        remove_path(path)

        IconScoreClassLoader.exit(self._SCORE_ROOT_PATH)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    @staticmethod
    def __unpack_zip_file(install_path: str, data: bytes):
        file_info_generator = IconScoreDeployer._extract_files_gen(data)
        for name, file_info, parent_directory in file_info_generator:
            if not os.path.exists(os.path.join(install_path, parent_directory)):
                os.makedirs(os.path.join(install_path, parent_directory))
            with file_info as file_info_context,\
                    open(os.path.join(install_path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)
        return True

    @staticmethod
    def __ensure_dir(file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def test_call_method(self):
        calldata = {'method': 'total_supply', 'params': {}}

        # proj_name = 'test_score'
        # path = os.path.join(TEST_ROOT_PATH, 'tests/tmp/{}'.format(proj_name))
        # install_data = {'contentType': 'application/tbears', 'content': path}
        # self._engine.invoke(
        #     self._context, self._icon_score_address, 'install', install_data)
        # self._engine.commit(self._context)
        context = IconScoreContext(IconScoreContextType.QUERY)

        with self.assertRaises(InvalidParamsException) as cm:
            self.engine.query(
                context, self._icon_score_address, 'call', calldata)

        e = cm.exception
        self.assertEqual(ExceptionCode.INVALID_PARAMS, e.code)
