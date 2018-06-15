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
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, IconServiceBaseException
from iconservice.logger.logger import Logger
from iconservice.icon_config import *
from iconservice.utils import make_response, make_error_response

from message_queue import message_queue_task, MessageQueueStub, MessageQueueService


class IconScoreInnerTask(object):
    def __init__(self, icon_score_root_path: str, icon_score_state_db_root_path: str):

        self.__icon_score_root_path = icon_score_root_path
        self.__icon_score_state_db_root_path = icon_score_state_db_root_path

        self.__icon_service_engine = IconServiceEngine()
        self.__is_open = False
        self.__type_converter = None
        self.__init_type_converter()

    def __init_type_converter(self):
        type_table = {
            'from': 'address',
            'to': 'address',
            'address': 'address',
            'fee': 'int',
            'value': 'int',
            'balance': 'int'
        }
        self.__type_converter = TypeConverter(type_table)

    @message_queue_task
    async def hello(self):
        Logger.info('icon_score_hello', ICON_INNER_LOG_TAG)

    @message_queue_task
    async def open(self):
        Logger.debug("icon_score_service open", ICON_INNER_LOG_TAG)
        self.__icon_service_engine.open(self.__icon_score_root_path, self.__icon_score_state_db_root_path)
        self.__is_open = True

    @message_queue_task
    async def close(self):
        Logger.debug("icon_score_service close", ICON_INNER_LOG_TAG)
        self.__icon_service_engine.close()
        self.__is_open = False

    @message_queue_task
    async def status(self):
        Logger.debug("icon_score_service status", ICON_INNER_LOG_TAG)
        result = dict()
        return make_response(result)

    @message_queue_task
    async def genesis_invoke(self, request: dict):
        Logger.debug(f'genesis invoke request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self.__check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            accounts = request.get('accounts')
            if accounts is None:
                response = make_error_response(ExceptionCode.INVALID_PARAMS, 'accounts is None')
            else:
                accounts = self.__type_converter.convert(accounts, recursive=False)
                self.__icon_service_engine.genesis_invoke(accounts)
                response = make_response(0)
        return response

    @message_queue_task
    async def invoke(self, request: dict):
        Logger.debug(f'invoke request with {request}', ICON_INNER_LOG_TAG)

        try:
            is_open, result = self.__check_open_icon_service_engine()

            if not is_open:
                response = result
            else:
                params = self.__type_converter.convert(request, recursive=False)
                block_params = params.get('block')
                transactions_params = params.get('transactions')
                converted_params = []
                for transaction_params in transactions_params:
                    converted_params.append(self.__type_converter.convert(transaction_params, recursive=True))

                if block_params is None or transactions_params is None:
                    response = make_error_response(ExceptionCode.INVALID_PARAMS, 'block_params, tx_params is None')
                else:
                    block = Block.create_block(block_params)
                    try:
                        tx_results = self.__icon_service_engine.invoke(block=block, tx_params=converted_params)
                        results = [tx_result.to_response_json() for tx_result in tx_results]
                        response = make_response(results)
                    finally:
                        pass
        finally:
            pass
        return response

    @message_queue_task
    async def query(self, request: dict):
        Logger.debug(f'query request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self.__check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
                method = request.get('method')
                params = request.get('params')
                params = self.__type_converter.convert(params, recursive=False)
                if method is None or params is None:
                    response = make_error_response(ExceptionCode.INVALID_PARAMS, 'method, params is None')
                else:
                    value = self.__icon_service_engine.query(method=method, params=params)
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
        Logger.debug(f'write_precommit_state request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self.__check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
                self.__icon_service_engine.commit()
                response = make_response(0)
            except IconServiceBaseException as icon_e:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
                return make_error_response(icon_e.code, icon_e.message)
            except Exception as e:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
                return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def remove_precommit_state(self, request: dict):
        Logger.debug(f'remove_precommit_state request with {request}', ICON_INNER_LOG_TAG)

        is_open, result = self.__check_open_icon_service_engine()
        if not is_open:
            response = result
        else:
            try:
                self.__icon_service_engine.rollback()
                response = make_response(0)
            except IconServiceBaseException as icon_e:
                Logger.error(icon_e, ICON_SERVICE_LOG_TAG)
                return make_error_response(icon_e.code, icon_e.message)
            except Exception as e:
                Logger.error(e, ICON_SERVICE_LOG_TAG)
                return make_error_response(ExceptionCode.SERVER_ERROR, str(e))
        return response

    @message_queue_task
    async def pre_validate_check(self, request: dict):
        response = make_response(0)
        return response

    def __check_open_icon_service_engine(self):
        if not self.__is_open:
            msg = "IconService isn't Open yet!!"
            Logger.error(msg, ICON_INNER_LOG_TAG)
            result = make_error_response(ExceptionCode.INVALID_REQUEST, msg)
        else:
            result = None

        return self.__is_open, result

    @message_queue_task
    async def change_block_hash(self, params):
        return 0


class IconScoreInnerService(MessageQueueService[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask


class IconScoreInnerStub(MessageQueueStub[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask
