# Copyright 2018 ICON Foundation
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

import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, TYPE_CHECKING, Optional, Tuple

from earlgrey import message_queue_task, MessageQueueStub, MessageQueueService
from iconcommons.logger import Logger

from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.base.exception import ExceptionCode, IconServiceBaseException, InvalidBaseTransactionException, \
    FatalException, ServiceNotReadyException
from iconservice.base.type_converter import TypeConverter, ParamType
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import ICON_INNER_LOG_TAG, ICON_SERVICE_LOG_TAG, \
    EnableThreadFlag, ENABLE_THREAD_FLAG
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.utils import check_error_response, to_camel_case

if TYPE_CHECKING:
    from earlgrey import RobustConnection
    from iconcommons.icon_config import IconConfig

THREAD_INVOKE = 'invoke'
THREAD_QUERY = 'query'
THREAD_VALIDATE = 'validate'


_TAG = ICON_INNER_LOG_TAG


class IconScoreInnerTask(object):
    def __init__(self, conf: 'IconConfig'):
        self._conf = conf
        self._thread_flag = ENABLE_THREAD_FLAG

        self._icon_service_engine = IconServiceEngine()
        self._open()

        self._thread_pool = {THREAD_INVOKE: ThreadPoolExecutor(1),
                             THREAD_QUERY: ThreadPoolExecutor(1),
                             THREAD_VALIDATE: ThreadPoolExecutor(1)}

    def _open(self):
        Logger.info(tag=_TAG, msg="_open() start")
        self._icon_service_engine.open(self._conf)
        Logger.info(tag=_TAG, msg="_open() end")

    def _is_thread_flag_on(self, flag: 'EnableThreadFlag') -> bool:
        return (self._thread_flag & flag) == flag

    def _check_icon_service_ready(self):
        if not self._icon_service_engine.is_reward_calculator_ready():
            raise ServiceNotReadyException("Reward Calculator is not ready")

    @staticmethod
    def _log_exception(e: BaseException, tag: str) -> None:
        Logger.exception(str(e), tag)
        Logger.error(str(e), tag)

    @message_queue_task
    async def hello(self):
        Logger.info(tag=_TAG, msg='hello() start')

        ready_future = self._icon_service_engine.get_ready_future()
        await ready_future

        if self._is_thread_flag_on(EnableThreadFlag.INVOKE):
            loop = asyncio.get_event_loop()
            ret = await loop.run_in_executor(self._thread_pool[THREAD_INVOKE], self._hello)
        else:
            ret = self._hello()

        Logger.info(tag=_TAG, msg='hello() end')

        return ret

    def _hello(self):
        return self._icon_service_engine.hello()

    def _close(self):
        Logger.info(tag=_TAG, msg="_close() start")

        if self._icon_service_engine:
            self._icon_service_engine.close()
            self._icon_service_engine = None
        MessageQueueService.loop.stop()

        Logger.info(tag=_TAG, msg="_close() end")

    @message_queue_task
    async def close(self):
        Logger.info(tag=_TAG, msg="close() start")

        self._close()

        Logger.info(tag=_TAG, msg="close() end")

    @message_queue_task
    async def invoke(self, request: dict) -> dict:
        Logger.debug(tag=_TAG, msg=f'invoke() start')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.INVOKE):
            loop = asyncio.get_event_loop()
            ret: dict = await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                                   self._invoke, request)
        else:
            ret: dict = self._invoke(request)

        Logger.debug(tag=_TAG, msg=f'invoke() end')
        return ret

    def _invoke(self, request: dict):
        """Process transactions in a block

        :param request:
        :return:
        """
        Logger.info(tag=_TAG, msg=f'INVOKE Request: {request}')

        response = None
        try:
            params = TypeConverter.convert(request, ParamType.INVOKE)
            converted_block_params = params['block']
            block = Block.from_dict(converted_block_params)

            converted_tx_requests = params['transactions']

            convert_tx_result_to_dict: bool = 'isBlockEditable' in params

            converted_is_block_editable = params.get('isBlockEditable', False)
            converted_prev_block_generator = params.get('prevBlockGenerator')
            converted_prev_block_validators = params.get('prevBlockValidators')
            converted_prev_votes = params.get('prevBlockVotes')

            tx_results, state_root_hash, added_transactions, main_prep_as_dict = self._icon_service_engine.invoke(
                block=block,
                tx_requests=converted_tx_requests,
                prev_block_generator=converted_prev_block_generator,
                prev_block_validators=converted_prev_block_validators,
                prev_block_votes=converted_prev_votes,
                is_block_editable=converted_is_block_editable)

            if convert_tx_result_to_dict:
                convert_tx_results = [tx_result.to_dict(to_camel_case) for tx_result in tx_results]
            else:
                # old version
                convert_tx_results = {bytes.hex(tx_result.tx_hash): tx_result.to_dict(to_camel_case)
                                      for tx_result in tx_results}
            results = {
                'txResults': convert_tx_results,
                'stateRootHash': bytes.hex(state_root_hash),
                'addedTransactions': added_transactions
            }

            if main_prep_as_dict:
                results["prep"] = main_prep_as_dict

            response = MakeResponse.make_response(results)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
            self._close()
        except InvalidBaseTransactionException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            if self._icon_service_engine:
                self._icon_service_engine.clear_context_stack()

            Logger.info(tag=_TAG, msg=f'INVOKE Response: {response}')
            return response

    @message_queue_task
    async def query(self, request: dict):
        # Logger.debug(tag=_TAG, msg=f'query request with {request}')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.QUERY):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_QUERY],
                                              self._query, request)
        else:
            return self._query(request)

    def _query(self, request: dict):
        response = None

        try:
            method = request['method']

            if method == 'debug_estimateStep':
                converted_request = TypeConverter.convert(request, ParamType.INVOKE_TRANSACTION)
                value = self._icon_service_engine.estimate_step(converted_request)
            else:
                converted_request = TypeConverter.convert(request, ParamType.QUERY)
                value = self._icon_service_engine.query(method, converted_request['params'])

            if isinstance(value, Address):
                value = str(value)
            response = MakeResponse.make_response(value)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            # Logger.debug(tag=_TAG, msg=f'query response with {response}')
            self._icon_service_engine.clear_context_stack()
            return response

    @message_queue_task
    async def call(self, request: dict):
        Logger.info(tag=_TAG, msg=f'call request with {request}')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.QUERY):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_QUERY],
                                              self._call, request)
        else:
            return self._call(request)

    def _call(self, request: dict):
        response = None

        try:
            response = self._icon_service_engine.inner_call(request)

            if isinstance(response, Address):
                response = str(response)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            Logger.info(tag=_TAG, msg=f'call response with {response}')
            return response

    @message_queue_task
    async def write_precommit_state(self, request: dict):
        Logger.info(tag=_TAG, msg=f'write_precommit_state request with {request}')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.INVOKE):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._write_precommit_state, request)
        else:
            return self._write_precommit_state(request)

    @staticmethod
    def _get_block_info_for_precommit_state(converted_block_params: dict) -> Tuple[int, bytes, Optional[bytes]]:
        block_height: int = converted_block_params[ConstantKeys.BLOCK_HEIGHT]
        block_hash: Optional[bytes] = None
        if ConstantKeys.BLOCK_HASH in converted_block_params:
            instant_block_hash: bytes = converted_block_params[ConstantKeys.BLOCK_HASH]
        else:
            instant_block_hash: bytes = converted_block_params[ConstantKeys.OLD_BLOCK_HASH]
            block_hash = converted_block_params[ConstantKeys.NEW_BLOCK_HASH]

        return block_height, instant_block_hash, block_hash

    def _write_precommit_state(self, request: dict):
        response = None
        try:
            converted_block_params = TypeConverter.convert(request, ParamType.WRITE_PRECOMMIT)
            block_height, instant_block_hash, block_hash = \
                self._get_block_info_for_precommit_state(converted_block_params)

            self._icon_service_engine.commit(block_height, instant_block_hash, block_hash)
            response = MakeResponse.make_response(ExceptionCode.OK)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
            self._close()
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            Logger.info(tag=_TAG, msg=f'write_precommit_state response with {response}')
            return response

    @message_queue_task
    async def remove_precommit_state(self, request: dict):
        Logger.info(tag=_TAG, msg=f'remove_precommit_state request with {request}')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.INVOKE):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_INVOKE],
                                              self._remove_precommit_state, request)
        else:
            return self._remove_precommit_state(request)

    def _remove_precommit_state(self, request: dict):
        response = None
        try:
            converted_block_params = TypeConverter.convert(request, ParamType.WRITE_PRECOMMIT)
            block_height, instant_block_hash, _ = \
                self._get_block_info_for_precommit_state(converted_block_params)

            self._icon_service_engine.remove_precommit_state(block_height, instant_block_hash)
            response = MakeResponse.make_response(ExceptionCode.OK)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
            self._close()
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            Logger.info(tag=_TAG, msg=f'remove_precommit_state response with {response}')
            return response

    @message_queue_task
    async def rollback(self, request: dict):
        """Go back to the state of the given previous block

        :param request:
        :return:
        """

        Logger.info(tag=_TAG, msg=f"rollback() start: {request}")

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.INVOKE):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(self._thread_pool[THREAD_INVOKE], self._rollback, request)
        else:
            response = self._rollback(request)

        Logger.info(tag=_TAG, msg=f"rollback() end: {response}")

        return response

    def _rollback(self, request: dict) -> dict:
        Logger.info(tag=_TAG, msg=f"_rollback() start: {request}")

        response = {}
        try:
            converted_params = TypeConverter.convert(request, ParamType.ROLLBACK)
            block_height: int = converted_params[ConstantKeys.BLOCK_HEIGHT]
            block_hash: bytes = converted_params[ConstantKeys.BLOCK_HASH]

            response: dict = self._icon_service_engine.rollback(block_height, block_hash)
            response = MakeResponse.make_response(response)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
            self._close()
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except BaseException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            Logger.info(tag=_TAG, msg=f"_rollback() end: {response}")
            return response

    @message_queue_task
    async def validate_transaction(self, request: dict):
        # Logger.debug(tag=_TAG, msg=f'pre_validate_check request with {request}')

        self._check_icon_service_ready()

        if self._is_thread_flag_on(EnableThreadFlag.VALIDATE):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._thread_pool[THREAD_VALIDATE],
                                              self._validate_transaction, request)
        else:
            return self._validate_transaction(request)

    def _validate_transaction(self, request: dict):
        response = None
        try:
            converted_request = TypeConverter.convert(
                request, ParamType.VALIDATE_TRANSACTION)
            self._icon_service_engine.validate_transaction(converted_request)
            response = MakeResponse.make_response(ExceptionCode.OK)
        except FatalException as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        except IconServiceBaseException as icon_e:
            self._log_exception(icon_e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(icon_e.code, icon_e.message)
        except Exception as e:
            self._log_exception(e, ICON_SERVICE_LOG_TAG)
            response = MakeResponse.make_error_response(ExceptionCode.SYSTEM_ERROR, str(e))
        finally:
            # Logger.debug(tag=_TAG, msg=f'pre_validate_check response with {response}')
            self._icon_service_engine.clear_context_stack()
            return response

    @message_queue_task
    async def change_block_hash(self, _params):

        self._check_icon_service_ready()

        return ExceptionCode.OK


class MakeResponse:
    @staticmethod
    def make_response(response: Any):
        if check_error_response(response):
            return response
        else:
            return TypeConverter.convert_type_reverse(response)

    @staticmethod
    def make_error_response(code: Any, message: str) -> dict:
        _code: int = int(code) + 32000
        return {'error': {'code': _code, 'message': message}}


class IconScoreInnerService(MessageQueueService[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask

    def _callback_connection_lost_callback(self, connection: 'RobustConnection'):
        Logger.error("MQ Connection lost. [Service]")
        # self.clean_close()

    def _callback_connection_reconnect_callback(self, connection: 'RobustConnection'):
        Logger.error("MQ Connection reconnect. [Service]")

    def clean_close(self):
        Logger.debug(tag=_TAG, msg="icon service will be closed while open the icon service engine. "
                                   "check if the config is valid")
        self._task._close()


class IconScoreInnerStub(MessageQueueStub[IconScoreInnerTask]):
    TaskType = IconScoreInnerTask

    def _callback_connection_lost_callback(self, connection: 'RobustConnection'):
        Logger.error("MQ Connection lost. [Stub]")
        # self._task._close()

    def _callback_connection_reconnect_callback(self, connection: 'RobustConnection'):
        Logger.error("MQ Connection reconnect. [Service]")
