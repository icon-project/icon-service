# Copyright 2017-2018 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any
from concurrent.futures.thread import ThreadPoolExecutor
from asyncio import get_event_loop

from iconservice.icon_service_engine import IconServiceEngine
from iconservice.base.type_converter import TypeConverter, ParamType
from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, IconServiceBaseException
from iconservice.logger.logger import Logger
from iconservice.icon_config import *
from iconservice.utils import check_error_response, to_camel_case

from earlgrey import message_queue_task, MessageQueueStub, MessageQueueService

THREAD_INVOKE = 'invoke'
THREAD_QUERY = 'query'
THREAD_VALIDATE = 'validate'


class IconScoreInnerTask(object):
    def __init__(self, icon_score_root_path: str, icon_score_state_db_root_path: str):

        self._icon_score_root_path = icon_score_root_path
        self._icon_score_state_db_root_path = icon_score_state_db_root_path

        self._icon_service_engine = IconServiceEngine()
        self._open()

        self._thread_pool = {THREAD_INVOKE: ThreadPoolExecutor(1),
                             THREAD_QUERY: ThreadPoolExecutor(1),
                             THREAD_VALIDATE: ThreadPoolExecutor(1)}

    def _open(self):
        Logger.debug("icon_score_service open", ICON_INNER_LOG_TAG)
        self._icon_service_engine.open(self._icon_score_root_path, self._icon_score_state_db_root_path)

    @message_queue_task
    async def hello(self):
        Logger.info('icon_score_hello', ICON_INNER_LOG_TAG)

    @message_queue_task
    async def close(self):
        Logger.debug("icon_score_service close", ICON_INNER_LOG_TAG)

        if self._icon_service_engine:
            self._icon_service_engine.close()
        MessageQueueService.loop.stop()

    @message_queue_task
    async def invoke(self, request: dict):
        Logger.debug(f'invoke request with {request}', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Invoke:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._invoke, request)
        else:
            return self._invoke(request)

    def _invoke(self, request: dict):
        response = None
        try:
            params = TypeConverter.convert(request, ParamType.INVOKE)
            converted_block_params = params['block']
            block = Block.from_dict(converted_block_params)
            self._icon_service_engine.validate_next_block(block)
            converted_tx_params = params['transactions']

            tx_results, state_root_hash = self._icon_service_engine.invoke(block=block, tx_params=converted_tx_params)
            convert_tx_results = \
                {bytes.hex(tx_result.tx_hash): tx_result.to_dict(to_camel_case) for tx_result in tx_results}
            results = {'txResults': convert_tx_results, 'stateRootHash': bytes.hex(state_root_hash)}
            response = MakeResponse.make_response(results)
        except IconServiceBaseException as icon_e:
            if DEV:
                Logger.exception(icon_e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            if DEV:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        finally:
            Logger.debug(f'invoke response with {response}', ICON_INNER_LOG_TAG)
            return response

    @message_queue_task
    async def query(self, request: dict):
        Logger.debug(f'query request with {request}', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Query:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_QUERY],
                                              self._query, request)
        else:
            return self._query(request)

    def _query(self, request: dict):
        response = None
        try:
            self._validate_jsonschema(request)
            converted_request = TypeConverter.convert(request, ParamType.QUERY)
            self._icon_service_engine.validate_for_query(converted_request)

            value = self._icon_service_engine.query(method=converted_request['method'],
                                                    params=converted_request['params'])

            if isinstance(value, Address):
                value = str(value)
            response = MakeResponse.make_response(value)
        except IconServiceBaseException as icon_e:
            if DEV:
                Logger.exception(icon_e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            if DEV:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        finally:
            Logger.debug(f'query response with {response}', ICON_INNER_LOG_TAG)
            return response

    @message_queue_task
    async def write_precommit_state(self, request: dict):
        Logger.debug(f'write_precommit_state request with {request}', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Invoke:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._write_precommit_state, request)
        else:
            return self._write_precommit_state(request)

    def _write_precommit_state(self, request: dict):
        response = None
        try:
            converted_block_params = TypeConverter.convert(request, ParamType.WRITE_PRECOMMIT)
            block = Block.from_dict(converted_block_params)
            self._icon_service_engine.validate_precommit(block)

            self._icon_service_engine.commit()
            response = MakeResponse.make_response(ExceptionCode.OK)
        except IconServiceBaseException as icon_e:
            if DEV:
                Logger.exception(icon_e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            if DEV:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        finally:
            Logger.debug(f'write_precommit_state response with {response}', ICON_INNER_LOG_TAG)
            return response

    @message_queue_task
    async def remove_precommit_state(self, request: dict):
        Logger.debug(f'remove_precommit_state request with {request}', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Invoke:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._remove_precommit_state, request)
        else:
            return self._remove_precommit_state(request)

    def _remove_precommit_state(self, request: dict):
        response = None
        try:
            converted_block_params = TypeConverter.convert(request, ParamType.WRITE_PRECOMMIT)
            block = Block.from_dict(converted_block_params)
            self._icon_service_engine.validate_precommit(block)

            self._icon_service_engine.rollback()
            response = MakeResponse.make_response(ExceptionCode.OK)
        except IconServiceBaseException as icon_e:
            if DEV:
                Logger.exception(icon_e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            if DEV:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        finally:
            Logger.debug(f'remove_precommit_state response with {response}', ICON_INNER_LOG_TAG)
            return response

    @message_queue_task
    async def validate_transaction(self, request: dict):
        Logger.debug(f'pre_validate_check request with {request}', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Validate:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_VALIDATE],
                                              self._validate_transaction, request)
        else:
            return self._validate_transaction(request)

    def _validate_transaction(self, request: dict):
        response = None
        try:
            self._validate_jsonschema(request)
            converted_request = TypeConverter.convert(request, ParamType.VALIDATE_TRANSACTION)
            self._icon_service_engine.validate_for_invoke(converted_request)
            response = MakeResponse.make_response(ExceptionCode.OK)
        except IconServiceBaseException as icon_e:
            if DEV:
                Logger.exception(icon_e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            if DEV:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
            else:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        finally:
            Logger.debug(f'pre_validate_check response with {response}', ICON_INNER_LOG_TAG)
            return response

    def _validate_jsonschema(self, request: dict):
        # TODO: Skip jsonschema validation
        # to support deprecated unittest using ICON JSON-RPC api v2
        # validate_jsonschema(request)
        pass

    @message_queue_task
    async def change_block_hash(self, params):
        return ExceptionCode.OK


class MakeResponse:
    @staticmethod
    def make_response(response: Any):
        if check_error_response(response):
            return response
        else:
            return MakeResponse.convert_type(response)

    @staticmethod
    def convert_type(value: Any):
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, bytes):
                    is_hash = k in ('blockHash', 'txHash')
                    value[k] = MakeResponse.convert_bytes(v, is_hash)
                else:
                    value[k] = MakeResponse.convert_type(v)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = MakeResponse.convert_type(v)
        elif isinstance(value, int):
            value = hex(value)
        elif isinstance(value, Address):
            value = str(value)
        elif isinstance(value, bytes):
            value = MakeResponse.convert_bytes(value)
        return value

    @staticmethod
    def convert_bytes(value: bytes, is_hash: bool = False):
        if is_hash:
            # if the value is of 'txHash' or 'blockHash', excludes '0x' prefix
            return bytes.hex(value)
        else:
            return f'0x{bytes.hex(value)}'

    @staticmethod
    def make_error_response(code: Any, message: str):
        return {'error': {'code': int(code), 'message': message}}


class IconScoreInnerService(MessageQueueService[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask


class IconScoreInnerStub(MessageQueueStub[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask
