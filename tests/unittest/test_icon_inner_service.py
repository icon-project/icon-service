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
import asyncio
import threading
from unittest.mock import Mock

import pytest
from iconcommons import IconConfig

from iconservice.base.exception import FatalException, InvalidBaseTransactionException, IconServiceBaseException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import RPCMethod, ENABLE_THREAD_FLAG
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_step import OutOfStepException
from tests import create_block_hash


@pytest.fixture(params=[ENABLE_THREAD_FLAG, ~ENABLE_THREAD_FLAG])
def inner_task(mocker, request):
    mocker.patch.object(IconScoreInnerTask, "_open")
    mocker.patch.object(IconScoreInnerTask, "_close")
    inner_task = IconScoreInnerTask(Mock(spec=IconConfig))
    inner_task._thread_flag = request.param
    icon_service_engine = Mock(spec=IconServiceEngine)
    inner_task._icon_service_engine = icon_service_engine

    return inner_task


@pytest.fixture()
def dummy_block():
    block = {
        ConstantKeys.BLOCK_HEIGHT: hex(0),
        ConstantKeys.BLOCK_HASH: create_block_hash().hex(),
        ConstantKeys.TIMESTAMP: hex(0),
        ConstantKeys.PREV_BLOCK_HASH: create_block_hash().hex()
    }
    return block


@pytest.fixture()
def dummy_invoke_request(dummy_block):
    return {"block": dummy_block, "transactions": []}


@pytest.fixture()
def dummy_write_precommit_request():
    return {
        ConstantKeys.BLOCK_HEIGHT: hex(0),
        ConstantKeys.BLOCK_HASH: create_block_hash().hex()
    }


@pytest.fixture()
def dummy_query_request():
    return {
        ConstantKeys.METHOD: "icx_call",
        ConstantKeys.PARAMS: {}
    }


IS_BASE_EXCEPTIONS = [exception("base exception") for exception in
                      IconServiceBaseException.__subclasses__() if exception != OutOfStepException]

EXCEPTIONS = [
    FatalException("fatal exception"),
    InvalidBaseTransactionException("exception"),
    Exception("exception")
]


class TestIconInnerService:

    def test_get_block_info_for_precommit_state(self):
        block_height = 10
        instant_block_hash = create_block_hash()
        block_hash = create_block_hash()

        # TEST: When input prev write pre-commit data format, block_hash should be None
        prev_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.BLOCK_HASH: instant_block_hash
        }

        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(prev_precommit_data_format)

        assert actual_block_height == block_height
        assert actual_instant_block_hash == instant_block_hash
        assert actual_block_hash is None

        # TEST: When input new write-pre-commit data format, block_hash should be hash
        new_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
            ConstantKeys.NEW_BLOCK_HASH: block_hash
        }

        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(new_precommit_data_format)

        assert actual_block_height == block_height
        assert actual_instant_block_hash == instant_block_hash
        assert actual_block_hash == block_hash

        # TEST: When input invalid data format, should raise key error
        invalid_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
        }

        with pytest.raises(KeyError) as e:
            IconScoreInnerTask._get_block_info_for_precommit_state(invalid_precommit_data_format)

    @pytest.mark.parametrize("exception, expected_msg, expected_code", [
        (exception, exception.args[0], 32001) for exception in EXCEPTIONS
    ])
    def test_fatal_exception_catch_on_invoke(self, exception, expected_msg, expected_code,
                                             inner_task, dummy_invoke_request):
        # invoke thread: invoke, write_precommit_state, remove_precommit_state
        def mocked_invoke(*args, **kwargs):
            raise exception

        inner_task._icon_service_engine.invoke = mocked_invoke
        loop = asyncio.get_event_loop()

        # Act
        response = loop.run_until_complete(inner_task.invoke(dummy_invoke_request))

        assert response['error']['code'] == expected_code
        assert response['error']['message'] == expected_msg
        if isinstance(exception, FatalException):
            # When FatalException having been raised on invoke
            # should close the icon service after sending error response
            assert inner_task._close.called
        else:
            assert not inner_task._close.called

    @pytest.mark.parametrize("exception, expected_msg, expected_code", [
        (exception, exception.message, 32000 + int(exception.code)) for exception in IS_BASE_EXCEPTIONS
    ])
    def test_is_base_exception_catch_on_invoke(self, exception, expected_msg, expected_code,
                                               inner_task, dummy_invoke_request):
        # When other exception having been raised, error response should be returned
        def mocked_invoke(*args, **kwargs):
            raise exception

        inner_task._icon_service_engine.invoke = mocked_invoke
        loop = asyncio.get_event_loop()

        # Act
        response = loop.run_until_complete(inner_task.invoke(dummy_invoke_request))

        assert response['error']['code'] == expected_code
        assert response['error']['message'] == expected_msg
        assert not inner_task._close.called

    @pytest.mark.parametrize("exception, expected_msg, expected_code", [
        (exception, exception.args[0], 32001) for exception in EXCEPTIONS
        if not isinstance(exception, InvalidBaseTransactionException)
    ])
    def test_exception_catch_on_write_precommit_state(self, exception, expected_msg, expected_code,
                                                      inner_task, dummy_write_precommit_request):
        def mocked_write_precommit(block_height, instant_block_hash, block_hash):
            raise exception

        inner_task._icon_service_engine.commit = mocked_write_precommit

        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(inner_task.write_precommit_state(dummy_write_precommit_request))

        assert response['error']['code'] == expected_code
        assert response['error']['message'] == expected_msg
        if isinstance(exception, FatalException):
            assert inner_task._close.called
        else:
            assert not inner_task._close.called

    @pytest.mark.parametrize("exception, expected_msg, expected_code", [
        (exception, exception.message, 32000 + int(exception.code)) for exception in IS_BASE_EXCEPTIONS
    ])
    def test_base_exception_catch_on_write_precommit_state(self, exception, expected_msg, expected_code,
                                                           inner_task, dummy_write_precommit_request):
        # When other exception having been raised, error response should be returned
        def mocked_write_precommit(block_height, instant_block_hash, block_hash):
            raise exception

        inner_task._icon_service_engine.commit = mocked_write_precommit
        loop = asyncio.get_event_loop()

        response = loop.run_until_complete(inner_task.write_precommit_state(dummy_write_precommit_request))

        assert response['error']['code'] == expected_code
        assert response['error']['message'] == expected_msg
        assert not inner_task._close.called

    @pytest.mark.parametrize("exception, expected_msg, expected_code",
                             [(exception, exception.args[0], 32001) for exception in EXCEPTIONS
                              if not isinstance(exception, InvalidBaseTransactionException)]
                             + [(exception, exception.message, 32000 + int(exception.code)) for exception in
                                IS_BASE_EXCEPTIONS])
    def test_exception_catch_on_query_thread(self, exception, expected_msg, expected_code,
                                             inner_task, dummy_query_request):
        # When FatalException having been raised on query, call (inner call),
        # should not close the icon service
        def mocked_query(method, params):
            raise exception

        inner_task._icon_service_engine.query = mocked_query
        loop = asyncio.get_event_loop()

        # Act
        response = loop.run_until_complete(inner_task.query(dummy_query_request))

        assert response['error']['code'] == expected_code
        assert response['error']['message'] == expected_msg
        assert not inner_task._close.called

    def test_query_thread_should_be_divided(self, inner_task):
        if inner_task._thread_flag == ~ENABLE_THREAD_FLAG:
            pytest.skip()
        status_list = [RPCMethod.ICX_GET_BALANCE,
                       RPCMethod.ISE_GET_STATUS,
                       RPCMethod.ICX_GET_TOTAL_SUPPLY,
                       RPCMethod.ICX_GET_SCORE_API]
        status_requests = [{
            ConstantKeys.METHOD: method,
            ConstantKeys.PARAMS: {}
        } for method in status_list]

        icx_call_request = {
            ConstantKeys.METHOD: RPCMethod.ICX_CALL,
            ConstantKeys.PARAMS: {}
        }

        estimate_request = {
            ConstantKeys.METHOD: RPCMethod.DEBUG_ESTIMATE_STEP,
            ConstantKeys.PARAMS: {}
        }

        def mocked_query(method, params):
            return threading.get_ident()

        def mocked_estimate(request):
            return threading.get_ident()

        loop = asyncio.get_event_loop()
        inner_task._icon_service_engine.query = mocked_query
        inner_task._icon_service_engine.estimate_step = mocked_estimate

        # Acts
        status_thread_ids = [loop.run_until_complete(inner_task.query(status_req)) for status_req in status_requests]
        call_thread_id = loop.run_until_complete(inner_task.query(icx_call_request))
        estimate_thread_id = loop.run_until_complete(inner_task.query(estimate_request))

        # Checks
        assert len(set(status_thread_ids)) == 1
        assert status_requests[0] != call_thread_id
        assert status_requests[0] != estimate_thread_id
        assert call_thread_id != estimate_thread_id

