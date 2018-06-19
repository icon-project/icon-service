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

from iconservice.icon_service_engine import IconServiceEngine
from iconservice.base.type_converter import TypeConverter
from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, IconServiceBaseException
from iconservice.logger.logger import Logger
from iconservice.icon_config import *
from iconservice.utils import make_response, make_error_response

from message_queue import message_queue_task, MessageQueueStub, MessageQueueService


class IconScoreInnerTask(object):
    def __init__(self, icon_score_root_path: str, icon_score_state_db_root_path: str):

        self._icon_score_root_path = icon_score_root_path
        self._icon_score_state_db_root_path = icon_score_state_db_root_path

        self._icon_service_engine = IconServiceEngine()
        self._is_open = False
        self._type_converter = None
        self._init_type_converter()

    def _init_type_converter(self):
        type_table = {
            'from': 'address',
            'to': 'address',
            'address': 'address',
            'fee': 'int',
            'value': 'int',
            'balance': 'int',
            'timestamp': 'int'
        }
        self._type_converter = TypeConverter(type_table)

    @message_queue_task
    async def hello(self):
        Logger.info('icon_score_hello', ICON_INNER_LOG_TAG)

    @message_queue_task
    async def open(self):
        if self._is_open:
            make_error_response(ExceptionCode.INVALID_REQUEST, 'already icon_service opened!')

        Logger.debug("icon_score_service open", ICON_INNER_LOG_TAG)
        self._icon_service_engine.open(self._icon_score_root_path, self._icon_score_state_db_root_path)
        self._is_open = True

    @message_queue_task
    async def close(self):
        Logger.debug("icon_score_service close", ICON_INNER_LOG_TAG)
        self._icon_service_engine.close()
        self._is_open = False

    @message_queue_task
    async def genesis_invoke(self, request: dict):
        Logger.debug(f'genesis invoke request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self._check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            accounts = request.get('accounts')
            if accounts is None:
                response = make_error_response(ExceptionCode.INVALID_PARAMS, 'accounts is None')
            else:
                accounts = self._type_converter.convert(accounts, recursive=False)
                self._icon_service_engine.genesis_invoke(accounts)
                response = make_response(ExceptionCode.OK)
        return response

    @message_queue_task
    async def invoke(self, request: dict):
        Logger.debug(f'invoke request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self._check_open_icon_service_engine()

        if not is_open:
            response = result
        else:
            params = self._type_converter.convert(request, recursive=False)
            block_params = params.get('block')
            transactions_params = params.get('transactions')

            converted_params = []
            for transaction_params in transactions_params:
                converted_params.append(self._type_converter.convert(transaction_params, recursive=True))

            if block_params is None or transactions_params is None:
                response = make_error_response(ExceptionCode.INVALID_PARAMS, 'block_params, tx_params is None')
            else:
                block = Block.create_block(block_params)
                tx_results = self._icon_service_engine.invoke(block=block, tx_params=converted_params)
                results = [tx_result.to_response_json() for tx_result in tx_results]
                response = make_response(results)
        return response

    @message_queue_task
    async def query(self, request: dict):
        Logger.debug(f'query request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self._check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
                converted_request = self._convert_request_params(request)
                self._icon_service_engine.query_pre_validate(converted_request)

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
    async def write_precommit_state(self):
        Logger.debug(f'write_precommit_state request', ICON_INNER_LOG_TAG)

        is_open, result = self._check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
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
    async def remove_precommit_state(self):
        Logger.debug(f'remove_precommit_state request', ICON_INNER_LOG_TAG)

        is_open, result = self._check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
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
    async def pre_validate_check(self, request: dict):
        try:
            converted_request = self._convert_request_params(request)
            self._icon_service_engine.tx_pre_validate(converted_request)
        except IconServiceBaseException as icon_e:
            Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
            return make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            Logger.error(e, ICON_SERVICE_LOG_TAG)
            return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return make_response(ExceptionCode.OK)

    def _check_open_icon_service_engine(self):
        if not self._is_open:
            msg = "IconService isn't opened yet!!"
            Logger.error(msg, ICON_INNER_LOG_TAG)
            result = make_error_response(ExceptionCode.INVALID_REQUEST, msg)
        else:
            result = None

        return self._is_open, result

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
