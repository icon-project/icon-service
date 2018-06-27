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

from concurrent.futures.thread import ThreadPoolExecutor
from asyncio import get_event_loop

from iconservice.icon_service_engine import IconServiceEngine
from iconservice.base.type_converter import TypeConverter
from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, IconServiceBaseException
from iconservice.logger.logger import Logger
from iconservice.icon_config import *
from iconservice.utils import make_response, make_error_response

from earlgrey import message_queue_task, MessageQueueStub, MessageQueueService

THREAD_INVOKE = 'invoke'
THREAD_QUERY = 'query'
THREAD_VALIDATE = 'validate'


class IconScoreInnerTask(object):
    def __init__(self, icon_score_root_path: str, icon_score_state_db_root_path: str):

        self._icon_score_root_path = icon_score_root_path
        self._icon_score_state_db_root_path = icon_score_state_db_root_path

        self._icon_service_engine = IconServiceEngine()
        self._type_converter = None
        self._init_type_converter()
        self._open()

        self._thread_pool = {THREAD_INVOKE: ThreadPoolExecutor(1),
                             THREAD_QUERY: ThreadPoolExecutor(1),
                             THREAD_VALIDATE: ThreadPoolExecutor(1)}

    def _open(self):
        Logger.debug("icon_score_service open", ICON_INNER_LOG_TAG)
        self._icon_service_engine.open(self._icon_score_root_path, self._icon_score_state_db_root_path)

    def _init_type_converter(self):
        type_table = {
            'from': 'address',
            'to': 'address',
            'address': 'address',
            'fee': 'int',
            'value': 'int',
            'balance': 'int',
            'stepLimit': 'int',
            'timestamp': 'int',
            'blockHeight': 'int'
        }
        self._type_converter = TypeConverter(type_table)

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
    async def genesis_invoke(self, request: dict):
        Logger.debug(f'genesis invoke request with {request}', ICON_INNER_LOG_TAG)
        return self._invoke(request)

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
        try:
            params = self._type_converter.convert(request, recursive=False)
            block_params = params['block']
            converted_block_params = self._type_converter.convert(block_params, recursive=True)

            block = Block.from_dict(converted_block_params)
            self._icon_service_engine.check_block_validate(block)

            transactions_params = params['transactions']

            converted_tx_params = []
            for transaction_params in transactions_params:
                converted_tx_params.append(self._type_converter.convert(transaction_params, recursive=True))

            tx_results = self._icon_service_engine.invoke(block=block, tx_params=converted_tx_params)
            results = {tx_result.tx_hash: tx_result.to_response_json() for tx_result in tx_results}
            response = make_response(results)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def query(self, request: dict):
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Query:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_QUERY],
                                              self._query, request)
        else:
            return self._query(request)

    def _query(self, request: dict):
        try:
            converted_request = self._convert_request_params(request)
            self._icon_service_engine.validate_for_query(converted_request)

            value = self._icon_service_engine.query(method=converted_request['method'],
                                                    params=converted_request['params'])

            if isinstance(value, Address):
                value = str(value)
            response = make_response(value)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def write_precommit_state(self, request: dict):
        Logger.debug(f'write_precommit_state request', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Invoke:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._write_precommit_state, request)
        else:
            return self._write_precommit_state(request)

    def _write_precommit_state(self, request: dict):
        try:
            converted_block_params = self._type_converter.convert(request, recursive=False)
            block = Block.from_dict(converted_block_params)
            self._icon_service_engine.validate_precommit(block)

            self._icon_service_engine.commit()
            response = make_response(ExceptionCode.OK)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def remove_precommit_state(self, request: dict):
        Logger.debug(f'remove_precommit_state request', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Invoke:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._remove_precommit_state, request)
        else:
            return self._remove_precommit_state(request)

    def _remove_precommit_state(self, request: dict):
        try:
            # TODO check block validate
            block = Block.from_dict(request)
            self._icon_service_engine.validate_precommit(block)

            self._icon_service_engine.rollback()
            response = make_response(ExceptionCode.OK)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def validate_transaction(self, request: dict):
        Logger.debug(f'pre_validate_check request', ICON_INNER_LOG_TAG)
        if ENABLE_INNER_SERVICE_THREAD & EnableThreadFlag.Validate:
            loop = get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_VALIDATE],
                                              self._validate_transaction, request)
        else:
            return self._validate_transaction(request)

    def _validate_transaction(self, request: dict):
        try:
            converted_request = self._convert_request_params(request)
            self._icon_service_engine.validate_for_invoke(converted_request)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return make_response(ExceptionCode.OK)

    def _convert_request_params(self, request: dict) -> dict:
        params = request['params']
        params = self._type_converter.convert(params, recursive=False)
        request['params'] = params
        return request

    @message_queue_task
    async def change_block_hash(self, params):
        return ExceptionCode.OK


class IconScoreInnerService(MessageQueueService[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask


class IconScoreInnerStub(MessageQueueStub[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask
