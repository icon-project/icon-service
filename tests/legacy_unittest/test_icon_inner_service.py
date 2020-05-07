# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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
from unittest.mock import Mock, patch

from iconcommons import IconConfig

from iconservice.base.exception import FatalException, InvalidBaseTransactionException, IconServiceBaseException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from tests import create_block_hash


class TestIconInnerService(unittest.TestCase):
    def setUp(self):
        self.icon_inner_task_open_patcher = patch('iconservice.icon_inner_service.IconScoreInnerTask._open')
        self.icon_inner_task_close_patcher = patch('iconservice.icon_inner_service.IconScoreInnerTask.close')
        _ = self.icon_inner_task_open_patcher.start()
        _ = self.icon_inner_task_close_patcher.start()

        IconScoreInnerTask._open = Mock()
        self.inner_task = IconScoreInnerTask(Mock(spec=IconConfig))
        icon_service_engine = Mock(spec=IconServiceEngine)
        self.inner_task._icon_service_engine = icon_service_engine

        block = {
            ConstantKeys.BLOCK_HEIGHT: hex(0),
            ConstantKeys.BLOCK_HASH: create_block_hash().hex(),
            ConstantKeys.TIMESTAMP: hex(0),
            ConstantKeys.PREV_BLOCK_HASH: create_block_hash().hex()
        }
        self.mocked_invoke_request = {"block": block, "transactions": []}
        self.mocked_write_precommit_request = {
            ConstantKeys.BLOCK_HEIGHT: hex(0),
            ConstantKeys.BLOCK_HASH: create_block_hash().hex()
        }
        self.mocked_query_request = {
            ConstantKeys.METHOD: "icx_call",
            ConstantKeys.PARAMS: {}
        }

        exception_msg = "non fatal exception"
        exception_list = [InvalidBaseTransactionException,
                          IconServiceBaseException,
                          Exception]
        self.exception_list = list(map(lambda exception: exception(exception_msg), exception_list))

    def tearDown(self):
        self.icon_inner_task_open_patcher.stop()
        self.icon_inner_task_close_patcher.stop()

    def test_get_block_info_for_precommit_state(self):
        block_height = 10
        instant_block_hash = create_block_hash()
        block_hash = create_block_hash()

        # success case: when input prev write pre-commit data format, block_hash should be None
        prev_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.BLOCK_HASH: instant_block_hash
        }
        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(prev_precommit_data_format)

        self.assertEqual(block_height, actual_block_height)
        self.assertEqual(instant_block_hash, actual_instant_block_hash)
        self.assertIsNone(actual_block_hash)

        # success case: when input new write-pre-commit data format, block_hash should be hash
        new_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
            ConstantKeys.NEW_BLOCK_HASH: block_hash
        }
        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(new_precommit_data_format)

        self.assertEqual(block_height, actual_block_height)
        self.assertEqual(instant_block_hash, actual_instant_block_hash)
        self.assertEqual(block_hash, actual_block_hash)

        # failure case: when input invalid data format, should raise key error
        invalid_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
        }
        self.assertRaises(KeyError,
                          IconScoreInnerTask._get_block_info_for_precommit_state,
                          invalid_precommit_data_format)

    def test_fatal_exception_catch_on_invoke(self):
        # invoke thread: invoke, write_precommit_state, remove_precommit_state

        # success case: when FatalException having been raised on invoke
        # should close the icon service after sending error response
        expected_error_msg = "fatal exception on invoke"
        expected_error_code = 32001

        def mocked_invoke(block,
                          tx_requests,
                          prev_block_generator,
                          prev_block_validators,
                          prev_block_votes,
                          is_block_editable):
            raise FatalException(expected_error_msg)

        self.inner_task._icon_service_engine.invoke = mocked_invoke
        response = self.inner_task._invoke(self.mocked_invoke_request)
        assert expected_error_code, response['error']['code']
        assert expected_error_msg, response['error']['message']
        assert self.inner_task.close.called

        self.inner_task.close.reset_mock()

        # success case: when other exception having been raised, error response should be returned
        for exception in self.exception_list:
            expected_error_msg = exception.args[0]

            def mocked_invoke(block,
                              tx_requests,
                              prev_block_generator,
                              prev_block_validators,
                              prev_block_votes,
                              is_block_editable):
                raise exception

            self.inner_task._icon_service_engine.invoke = mocked_invoke
            response = self.inner_task._invoke(self.mocked_invoke_request)
            assert expected_error_msg, response['error']['message']
            assert not self.inner_task.close.called
            self.inner_task.close.reset_mock()

    def test_fatal_exception_catch_on_write_precommit_state(self):
        # success case: when FatalException having been raised on write_precommit_state,
        # should close the icon service after sending error response
        expected_error_msg = "fatal exception on write_precommit_state"
        expected_error_code = 32001

        def mocked_write_precommit(block_height, instant_block_hash, block_hash):
            raise FatalException(expected_error_msg)

        self.inner_task._icon_service_engine.commit = mocked_write_precommit
        response = self.inner_task._write_precommit_state(self.mocked_write_precommit_request)
        assert expected_error_code, response['error']['code']
        assert expected_error_msg, response['error']['message']
        assert self.inner_task.close.called

        self.inner_task.close.reset_mock()

        # success case: when other exception having been raised, error response should be returned
        for exception in self.exception_list:
            expected_error_msg = exception.args[0]

            def mocked_write_precommit(block_height, instant_block_hash, block_hash):
                raise exception

            self.inner_task._icon_service_engine.invoke = mocked_write_precommit
            response = self.inner_task._invoke(self.mocked_write_precommit_request)
            assert expected_error_msg, response['error']['message']
            assert not self.inner_task.close.called
            self.inner_task.close.reset_mock()

    def test_fatal_exception_catch_on_query_thread(self):
        # query thread: query

        # success case: when FatalException having been raised on query, call (inner call),
        # should not close the icon service
        expected_error_msg = "fatal exception on query"
        expected_error_code = 32001

        def mocked_query(method,
                         params):
            raise FatalException(expected_error_msg)

        self.inner_task._icon_service_engine.query = mocked_query
        response = self.inner_task._query(self.mocked_query_request)
        assert expected_error_code, response['error']['code']
        assert expected_error_msg, response['error']['message']
        assert not self.inner_task.close.called

        self.inner_task.close.reset_mock()

        # success case: when other exception having been raised, error response should be returned
        for exception in self.exception_list:
            expected_error_msg = exception.args[0]

            def mocked_query(method,
                             params):
                raise exception

            self.inner_task._icon_service_engine.invoke = mocked_query
            response = self.inner_task._query(self.mocked_query_request)
            assert expected_error_msg, response['error']['message']
            assert not self.inner_task.close.called
            self.inner_task.close.reset_mock()
