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
from unittest.mock import Mock, patch

from iconservice import *
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, Address
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, InvalidParamsException, ServerErrorException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.icx.icx_storage import IcxStorage
from tests import create_tx_hash, create_block_hash
from tests import rmtree, create_address

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreEngine(unittest.TestCase):
    _ROOT_SCORE_PATH = os.path.join(TEST_ROOT_PATH, 'score')
    _TEST_DB_PATH = 'tests/test_db/'

    def setUp(self):
        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

        archive_path = 'tests/sample/valid.zip'
        archive_path = os.path.join(TEST_ROOT_PATH, archive_path)
        zip_bytes = self.read_zipfile_as_byte(archive_path)
        install_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self.__unpack_zip_file(install_path, zip_bytes)

        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        ContextDatabaseFactory.open(
            db_path, ContextDatabaseFactory.Mode.SINGLE_DB)

        self.__ensure_dir(db_path)

        icx_db = ContextDatabaseFactory.create_by_name('icx_db')
        self.icx_storage = IcxStorage(icx_db)
        deploy_storage = IconScoreDeployStorage(self.icx_storage.db)
        deploy_engine = IconScoreDeployEngine()
        deploy_engine.open(self._ROOT_SCORE_PATH, deploy_storage)

        self.icon_score_loader = IconScoreLoader(self._ROOT_SCORE_PATH)

        IconScoreMapper.icon_score_loader = self.icon_score_loader
        IconScoreMapper.deploy_storage = deploy_storage
        self.icon_score_mapper = IconScoreMapper()

        self.engine = IconScoreEngine()

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

        remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)

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

    # FIXME
    # def test_install(self):
    #     proj_name = 'test_score'
    #     path = os.path.join(TEST_ROOT_PATH, 'tests/tmp/{}'.format(proj_name))
    #     install_data = {'contentType': 'application/tbears', 'content': path}
    #     self._engine.invoke(
    #         self._context, self._icon_score_address, 'install', install_data)
    #     self._engine.commit(self._context)

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
        print(e)

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.validate_score_blacklist')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._fallback')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._call')
    def test_invoke(self,
                    mocked_score_engine_call,
                    mocked_score_engine_fallback,
                    mocked_score_context_util_validate_score_blacklist):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        data_type = 'call'
        data = {}
        # check the address: None, zero_score_addresss, not contract
        # failure case: should not accept ZERO_SCORE_ADDRESS as SCORE address
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.invoke,
                          context, ZERO_SCORE_ADDRESS, data_type, data)

        # failure case: should not accept EOA as SCORE address
        eoa_address = create_address(AddressPrefix.EOA)
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.invoke,
                          context, eoa_address, data_type, data)

        # failure case: should not accept None type as SCORE address
        none_address = None
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.invoke,
                          context, none_address, data_type, data)

        # success case: valid score. if data type is 'call', _call method should be called
        mocked_score_engine_call.return_value = None
        mocked_score_engine_fallback.return_value = None
        mocked_score_context_util_validate_score_blacklist.return_value = None

        contract_address = create_address(AddressPrefix.CONTRACT)
        IconScoreEngine.invoke(context, contract_address, data_type, data)
        mocked_score_context_util_validate_score_blacklist.assert_called()
        mocked_score_engine_call.assert_called()
        mocked_score_engine_fallback.assert_not_called()

        # success case: valid score. if data type is not 'call', fallback method should be called
        data_type = ''
        mocked_score_engine_call.reset_mock(return_value=None)
        mocked_score_engine_fallback.reset_mock(return_value=None)
        mocked_score_context_util_validate_score_blacklist.reset_mock(return_value=None)

        IconScoreEngine.invoke(context, contract_address, data_type, data)
        mocked_score_context_util_validate_score_blacklist.assert_called()
        mocked_score_engine_call.assert_not_called()
        mocked_score_engine_fallback.assert_called()

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.validate_score_blacklist')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._fallback')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._call')
    def test_query(self,
                   mocked_score_engine_call,
                   mocked_score_engine_fallback,
                   mocked_score_context_util_validate_score_blacklist):
        context = IconScoreContext(IconScoreContextType.QUERY)
        data_type = 'call'
        data = {}
        # check the address: None, zero_score_addresss, not contract
        # failure case: should not accept ZERO_SCORE_ADDRESS as SCORE address
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.query,
                          context, ZERO_SCORE_ADDRESS, data_type, data)

        # failure case: should not accept EOA as SCORE address
        eoa_address = create_address(AddressPrefix.EOA)
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.query,
                          context, eoa_address, data_type, data)

        # failure case: should not accept None type as SCORE address
        none_address = None
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.query,
                          context, none_address, data_type, data)

        # success case: valid score. if data type is 'call', _call method should be called
        mocked_score_engine_call.return_value = "_call_method_return_data"
        mocked_score_engine_fallback.return_value = None
        mocked_score_context_util_validate_score_blacklist.return_value = None

        contract_address = create_address(AddressPrefix.CONTRACT)
        result = IconScoreEngine.query(context, contract_address, data_type, data)

        self.assertEqual(result, "_call_method_return_data")
        mocked_score_context_util_validate_score_blacklist.assert_called()
        mocked_score_engine_call.assert_called()
        mocked_score_engine_fallback.assert_not_called()

        # success case: valid score. if data type is not 'call', exception should be raised
        data_type = ''
        mocked_score_engine_call.reset_mock(return_value=None)
        mocked_score_engine_fallback.reset_mock(return_value=None)
        mocked_score_context_util_validate_score_blacklist.reset_mock(return_value=None)

        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.query,
                          context, contract_address, data_type, data)
        mocked_score_context_util_validate_score_blacklist.assert_called()
        mocked_score_engine_call.assert_not_called()

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_icon_score')
    def test_get_score_api(self, mocked_score_context_util_get_icon_score):
        # failure case: retrieve icon_score from get_icon_score()
        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.new_icon_score_mapper = IconScoreMapper()
        eoa_address = create_address(AddressPrefix.EOA)
        self.assertRaises(InvalidParamsException, IconScoreEngine.get_score_api, context, eoa_address)

        # get_score_api is called some user
        # failure case: should raise error if there is no SCORE
        score_address = create_address(AddressPrefix.CONTRACT)
        mocked_score_context_util_get_icon_score.return_value = None
        self.assertRaises(ServerErrorException, IconScoreEngine.get_score_api, context, score_address)

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._convert_score_params_by_annotations')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._get_icon_score')
    def test_call(self,
                  mocked_score_engine_get_icon_score,
                  mocked_score_engine_convert_score_params_by_annotations):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.new_icon_score_mapper = IconScoreMapper()

        def intercept_score_base_call(func_name: str, kw_params: dict):
            self.assertEqual(func_name, 'score_method')
            # should be converted_params
            self.assertEqual(kw_params, converted_params)
            return "__call method called"

        score_address = Mock(spec=Address)
        score_object = Mock(spec=IconScoreBase)
        mocked_score_engine_get_icon_score.return_value = score_object

        primitive_params = {"address": str(create_address(AddressPrefix.EOA)),
                            "integer": "0x10"}
        converted_params = {"address": create_address(AddressPrefix.EOA),
                            "integer": 10}
        mocked_score_engine_convert_score_params_by_annotations.return_value = converted_params
        context.set_func_type_by_icon_score = Mock()
        setattr(score_object, '_IconScoreBase__call', Mock(side_effect=intercept_score_base_call))

        # set method, and params, method is cannot be None as pre-validate it
        data = {'method': 'score_method',
                'params': primitive_params}
        result = IconScoreEngine._call(context, score_address, data)

        self.assertEqual(result, "__call method called")
        IconScoreEngine._get_icon_score.assert_called()
        IconScoreEngine._convert_score_params_by_annotations.assert_called()
        context.set_func_type_by_icon_score.assert_called()
        call = getattr(score_object, '_IconScoreBase__call')
        call.assert_called()

    def test_convert_score_params_by_annotations(self):
        # main function is to converting params based on method annotation
        def test_method(address: Address, integer: int):
            pass

        # success case: valid params and method
        primitive_params = {"address": str(create_address(AddressPrefix.EOA)),
                            "integer": "0x10"}
        score_object = Mock(spec=IconScoreBase)
        score_object.validate_external_method = Mock()
        setattr(score_object, 'test_method', test_method)
        converted_params = \
            IconScoreEngine._convert_score_params_by_annotations(score_object, 'test_method', primitive_params)

        score_object.validate_external_method.assert_called()
        # primitive_params must not be changed.
        self.assertEqual(type(primitive_params["address"]), str)
        self.assertEqual(type(converted_params["address"]), Address)

        # failure case: if arguments' type and parameters' type of method does not match, should raise an error
        not_matching_type_params = {"address": b'bytes_data',
                                    "integer": "string_data"}

        self.assertRaises(InvalidParamsException,
                          IconScoreEngine._convert_score_params_by_annotations,
                          score_object, 'test_method', not_matching_type_params)

        # success case: even though not enough number of params inputted, doesn't raise an error
        # parameter check is processed when executing method.
        score_object.validate_external_method.reset_mock()
        insufficient_params = {"address": str(create_address(AddressPrefix.EOA))}
        converted_params = \
            IconScoreEngine._convert_score_params_by_annotations(score_object, 'test_method', insufficient_params)
        score_object.validate_external_method.assert_called()
        self.assertEqual(type(insufficient_params["address"]), str)
        self.assertEqual(type(converted_params["address"]), Address)

    def test_fallback(self):
        pass
