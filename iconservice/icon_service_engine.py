# -*- coding: utf-8 -*-
# Copyright 2017-2018 theloop Inc.
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


from collections import namedtuple
from math import ceil
from os import makedirs
from typing import TYPE_CHECKING, Any, List, Optional

from .icon_constant import ICON_DEX_DB_NAME, ICON_SERVICE_LOG_TAG, DATA_BYTE_ORDER,\
    IconServiceFlag, IconDeployFlag, ConfigKey
from .utils import byte_length_of_int, is_lowercase_hex_string
from .utils.bloom import BloomFilter
from .base.address import Address, AddressPrefix
from .base.address import ICX_ENGINE_ADDRESS, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from .base.block import Block
from .base.exception import ExceptionCode, RevertException
from .base.exception import IconServiceBaseException, ServerErrorException
from .base.message import Message
from .base.transaction import Transaction
from .database.batch import BlockBatch, TransactionBatch
from .database.factory import DatabaseFactory
from .deploy.icon_score_deploy_engine import IconScoreDeployEngine
from .deploy.icon_score_manager import IconScoreManager
from .deploy.icon_builtin_score_loader import IconBuiltinScoreLoader
from .iconscore.icon_pre_validator import IconPreValidator
from .iconscore.icon_score_context import IconScoreContext, ContextContainer
from .iconscore.icon_score_context import IconScoreContextFactory
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .iconscore.icon_score_loader import IconScoreLoader
from .iconscore.icon_score_result import TransactionResult
from .iconscore.icon_score_step import IconScoreStepCounterFactory, StepType
from .iconscore.icon_score_trace import Trace, TraceType
from .deploy.icon_score_deploy_storage import IconScoreDeployStorage
from .icx.icx_account import AccountType
from .icx.icx_engine import IcxEngine
from .icx.icx_storage import IcxStorage
from iconcommons.logger import Logger

if TYPE_CHECKING:
    from .iconscore.icon_score_step import IconScoreStepCounter
    from .iconscore.icon_score_event_log import EventLog
    from iconcommons.icon_config import IconConfig


def _generate_score_address_for_tbears(score_path: str) -> 'Address':
    """

    :param score_path: The path of a SCORE which is under development with tbears
    :return:
    """
    project_name = score_path.split('/')[-1]
    return Address.from_data(AddressPrefix.CONTRACT, project_name.encode())


def _generate_score_address(from_: 'Address',
                            timestamp: int,
                            nonce: int = None) -> 'Address':
    """Generates a SCORE address from the transaction information.

    :param from_:
    :param timestamp:
    :param nonce:
    :return: score address
    """
    data = from_.body + timestamp.to_bytes(32, DATA_BYTE_ORDER)
    if nonce:
        data += nonce.to_bytes(32, DATA_BYTE_ORDER)

    return Address.from_data(AddressPrefix.CONTRACT, data)


class IconServiceEngine(ContextContainer):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconInnerService.
    """

    def __init__(self) -> None:
        """Constructor

        TODO: default flags?
        """
        self._conf = None
        self._flag = None
        self._db_factory = None
        self._context_factory = None
        self._icon_score_loader = None
        self._icx_context_db = None
        self._icx_storage = None
        self._icx_engine = None
        self._icon_score_mapper = None
        self._icon_score_engine = None
        self._icon_score_deploy_engine = None
        self._step_counter_factory = None
        self._precommit_state = None
        self._icon_pre_validator = None
        self._icon_score_deploy_storage = None

        # JSON-RPC handlers
        self._handlers = {
            'icx_getBalance': self._handle_icx_get_balance,
            'icx_getTotalSupply': self._handle_icx_get_total_supply,
            'icx_call': self._handle_icx_call,
            'icx_sendTransaction': self._handle_icx_send_transaction,
            'icx_getScoreApi': self._handle_icx_get_score_api
        }

        # The precommit state is the state that has already been invoked,
        # but not written to levelDB or file system.
        self._PrecommitState = namedtuple(
            'PrecommitState', ['block_batch', 'block_result'])

    def _is_flag_on(self, flag: 'IconServiceFlag') -> bool:
        return (self._flag & flag) == flag

    def open(self, conf: 'IconConfig') -> None:
        """Get necessary parameters and initialize diverse objects

        :param conf:
        """

        self._conf = conf
        self._flag = self._conf[ConfigKey.ICON_SERVICE_FLAG]
        icon_score_root_path = self._conf[ConfigKey.ICON_SCORE_ROOT]
        state_db_root_path = self._conf[ConfigKey.ICON_SCORE_STATE_DB_ROOT_PATH]

        makedirs(icon_score_root_path, exist_ok=True)
        makedirs(state_db_root_path, exist_ok=True)

        self._db_factory = DatabaseFactory(state_db_root_path)
        self._context_factory = IconScoreContextFactory(max_size=5)
        self._icon_score_loader = IconScoreLoader(icon_score_root_path)

        self._icx_engine = IcxEngine()
        self._icon_score_engine = IconScoreEngine()
        self._icon_score_deploy_engine = IconScoreDeployEngine()

        icon_score_manger = IconScoreManager(self._icon_score_deploy_engine)

        self._icx_context_db = self._db_factory.create_by_name(ICON_DEX_DB_NAME)
        self._icx_context_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_context_db)
        self._icon_score_deploy_storage = IconScoreDeployStorage(self._icx_context_db)

        self._icon_score_mapper = IconScoreInfoMapper(
            self._db_factory, icon_score_manger, self._icon_score_loader)

        self._step_counter_factory = IconScoreStepCounterFactory()
        self._icon_pre_validator = IconPreValidator(self._icx_engine, icon_score_manger)

        IconScoreContext.icx = self._icx_engine
        IconScoreContext.icon_score_mapper = self._icon_score_mapper
        IconScoreContext.icon_score_manager = icon_score_manger

        self._icx_engine.open(self._icx_storage)
        self._icon_score_engine.open(
            self._icx_storage, self._icon_score_mapper)

        icon_score_deploy_engine_flags = IconDeployFlag.NONE.value
        if self._is_flag_on(IconServiceFlag.ENABLE_AUDIT):
            icon_score_deploy_engine_flags = IconDeployFlag.ENABLE_DEPLOY_AUDIT.value
        self._icon_score_deploy_engine.open(
            icon_score_root_path=icon_score_root_path,
            flag=icon_score_deploy_engine_flags,
            icon_score_mapper=self._icon_score_mapper,
            icon_deploy_storage=self._icon_score_deploy_storage)

        self._load_builtin_scores()
        self._init_global_value_by_governance_score()

    def _load_builtin_scores(self):
        context = self._context_factory.create(IconScoreContextType.DIRECT)
        try:
            self._put_context(context)
            icon_builtin_score_loader = IconBuiltinScoreLoader(self._icon_score_deploy_engine)
            icon_builtin_score_loader.load_builtin_scores(context, self._conf[ConfigKey.ADMIN_ADDRESS])
        finally:
            self._delete_context(context)

    def _init_global_value_by_governance_score(self):
        context = self._context_factory.create(IconScoreContextType.DIRECT)
        try:
            self._put_context(context)
            governance_score = self._icon_score_mapper.get_icon_score(
                context, GOVERNANCE_SCORE_ADDRESS)
            if governance_score is None:
                raise ServerErrorException(f'governance_score is None')

            if self._is_flag_on(IconServiceFlag.ENABLE_FEE):
                step_price = governance_score.getStepPrice()
            else:
                step_price = 0

            self._step_counter_factory.set_step_price(step_price)

            step_costs = governance_score.getStepCosts()

            for key, value in step_costs.items():
                self._step_counter_factory.set_step_cost(StepType(key), value)
        finally:
            self._delete_context(context)

    def close(self) -> None:
        """Free all resources occupied by IconServiceEngine
        including db, memory and so on
        """

        self._icx_engine.close()
        self._icon_score_mapper.close()

    def invoke(self,
               block: 'Block',
               tx_requests: list) -> tuple:
        """Process transactions in a block sent by loopchain

        :param block:
        :param tx_requests: transactions in a block
        :return: (TransactionResult[], bytes)
        """
        self._init_global_value_by_governance_score()

        context = self._context_factory.create(IconScoreContextType.INVOKE)
        context.block = block
        context.block_batch = BlockBatch(Block.from_block(block))
        context.tx_batch = TransactionBatch()
        block_result = []

        if block.height == 0:
            # Assume that there is only one tx in genesis_block
            tx_result = self._invoke_genesis(context, tx_requests[0], 0)
            block_result.append(tx_result)
            context.block_batch.put_tx_batch(context.tx_batch)
            context.tx_batch.clear()
        else:
            for index, tx_request in enumerate(tx_requests):
                tx_result = self._invoke_request(context, tx_request, index)
                block_result.append(tx_result)
                context.block_batch.put_tx_batch(context.tx_batch)
                context.tx_batch.clear()

        # precommit_state will be written to levelDB on commit()
        self._precommit_state = self._PrecommitState(
            block_batch=context.block_batch,
            block_result=block_result)

        self._context_factory.destroy(context)

        return block_result, self._precommit_state.block_batch.digest()

    def validate_next_block(self, block: 'Block') -> None:
        last_block = self._icx_storage.last_block
        if last_block is None:
            return

        if block.height != last_block.height + 1:
            raise ServerErrorException(
                f'NextBlockHeight[{block.height}] '
                f'!= LastBlockHeight[{last_block.height}] + 1')
        elif block.prev_hash != last_block.hash:
            raise ServerErrorException(
                f'NextBlock.prevHash[{block.prev_hash}] '
                f'!= LastBlockHash[{last_block.hash}]')

    @staticmethod
    def _is_genesis_block(
            tx_index: int, block_height: int, tx_params: dict) -> bool:

        return block_height == 0\
               and tx_index == 0\
               and 'genesisData' in tx_params

    def _invoke_genesis(self,
                        context: 'IconScoreContext',
                        tx_params: dict,
                        index: int) -> 'TransactionResult':

        params = tx_params['params']
        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=index,
                                 origin=None,
                                 timestamp=context.block.timestamp,
                                 nonce=params.get('nonce', None))

        tx_result = TransactionResult(context.tx, context.block)

        try:
            genesis_data = tx_params['genesisData']
            accounts = genesis_data['accounts']

            genesis = accounts[0]
            treasury = accounts[1]
            others = accounts[2:]

            __NAME_KEY = 'name'
            __ADDRESS_KEY = 'address'
            __AMOUNT_KEY = 'balance'

            self._icx_engine.init_account(
                context=context,
                account_type=AccountType.GENESIS,
                account_name=genesis[__NAME_KEY],
                address=genesis[__ADDRESS_KEY],
                amount=genesis[__AMOUNT_KEY])

            self._icx_engine.init_account(
                context=context,
                account_type=AccountType.TREASURY,
                account_name=treasury[__NAME_KEY],
                address=treasury[__ADDRESS_KEY],
                amount=treasury[__AMOUNT_KEY])

            for other in others:
                self._icx_engine.init_account(
                    context=context,
                    account_type=AccountType.GENERAL,
                    account_name=other[__NAME_KEY],
                    address=other[__ADDRESS_KEY],
                    amount=other[__AMOUNT_KEY])

            tx_result.status = TransactionResult.SUCCESS

        except IconServiceBaseException as e:
            Logger.exception(e.message, ICON_SERVICE_LOG_TAG)
            # Add failure info to transaction result
            tx_result.failure = TransactionResult.Failure(
                code=e.code, message=e.message)
        except Exception as e:
            Logger.exception(e, ICON_SERVICE_LOG_TAG)
            tx_result.failure = TransactionResult.Failure(
                code=ExceptionCode.SERVER_ERROR, message=str(e))

        return tx_result

    def _invoke_request(self,
                        context: 'IconScoreContext',
                        request: dict,
                        index: int) -> 'TransactionResult':
        """Invoke a transaction request

        :param context:
        :param request:
        :param index:
        :return:
        """

        method = request['method']
        params = request['params']

        from_ = params['from']
        to = params['to']
        step_limit = params.get('stepLimit', 0)

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=index,
                                 origin=from_,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))

        context.msg = Message(sender=from_, value=params.get('value', 0))
        context.current_address = to
        context.event_logs: List['EventLog'] = []
        context.logs_bloom: BloomFilter = BloomFilter()
        context.traces: List['Trace'] = []
        context.step_counter: IconScoreStepCounter = \
            self._step_counter_factory.create(step_limit)
        context.clear_msg_stack()

        return self._call(context, method, params)

    def query(self, method: str, params: dict) -> Any:
        """Process a query message call from outside

        State change is not allowed in a query message call

        * icx_getBalance
        * icx_getTotalSupply
        * icx_call

        :param method:
        :param params:
        :return: the result of query
        """
        context = self._context_factory.create(IconScoreContextType.QUERY)
        context.block = self._icx_storage.last_block

        if params:
            from_ = params.get('from', None)
            context.msg = Message(sender=from_)

        ret = self._call(context, method, params)

        self._context_factory.destroy(context)

        return ret

    def validate_transaction(self, request: dict) -> None:
        """Validate JSON-RPC transaction request
        before putting it into transaction pool

        JSON Schema validator checks basic JSON-RPC request syntax
        on JSON-RPC Server
        IconPreValidator focuses on business logic and semantic problems

        :param request: JSON-RPC request
            values in request have already been converted to original format
            in IconInnerService
        :return:
        """
        assert request['method'] == 'icx_sendTransaction'
        assert 'params' in request

        params: dict = request['params']
        step_price: int = self._get_step_price()
        self._icon_pre_validator.execute(params, step_price)

    def _call(self,
              context: 'IconScoreContext',
              method: str,
              params: dict) -> Any:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have already been converted to the proper types.
        (types: Address, int, str, bool, bytes and array)

        invoke: Changes states of icon scores or icx
        query: query states of icon scores or icx without state changing

        :param context:
        :param method: 'icx_sendTransaction' only
        :param params: params in jsonrpc message
        :return:
            icx_sendTransaction: (bool) True(success) or False(failure)
            icx_getBalance, icx_getTotalSupply, icx_call:
                (dict) result or error object in jsonrpc response
        """

        self._put_context(context)
        handler = self._handlers[method]
        ret_val = handler(context, params)
        self._delete_context(context)
        return ret_val

    def _handle_icx_get_balance(self,
                                context: 'IconScoreContext',
                                params: dict) -> int:
        """Returns the icx balance of the given address

        :param context:
        :param params:
        :return: icx balance in loop
        """
        address = params['address']
        return self._icx_engine.get_balance(context, address)

    def _handle_icx_get_total_supply(self,
                                     context: 'IconScoreContext',
                                     params: dict) -> int:
        """Returns the amount of icx total supply

        :param context:
        :return: icx amount in loop (1 icx == 1e18 loop)
        """
        return self._icx_engine.get_total_supply(context)

    def _handle_icx_call(self,
                         context: 'IconScoreContext',
                         params: dict) -> object:
        """Handles an icx_call jsonrpc request

        State change is possible in icx_call message

        :param params:
        :return:
        """
        icon_score_address: Address = params['to']
        data_type = params.get('dataType', None)
        data = params.get('data', None)

        return self._icon_score_engine.query(context,
                                             icon_score_address,
                                             data_type,
                                             data)

    def _handle_icx_send_transaction(self,
                                     context: 'IconScoreContext',
                                     params: dict) -> 'TransactionResult':
        """icx_sendTransaction message handler

        * EOA to EOA
        * EOA to SCORE

        :param params: JSON-RPC params
        :return: return value of an IconScoreBase method
            None is allowed
        """
        tx_result = TransactionResult(context.tx, context.block)

        try:
            to: Address = params['to']
            tx_result.to = to

            # Check if from account can charge a tx fee
            self._icon_pre_validator.execute_to_check_out_of_balance(
                params,
                step_price=context.step_counter.step_price)

            # Every send_transaction are calculated DEFAULT STEP at first
            context.step_counter.apply_step(StepType.DEFAULT, 1)
            input_size = self._get_byte_length(params.get('data', None))

            context.step_counter.apply_step(StepType.INPUT, input_size)
            self._transfer_coin(context, params)

            if to.is_contract:
                tx_result.score_address =\
                    self._handle_score_invoke(context, to, params)

            tx_result.status = TransactionResult.SUCCESS
        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)
            trace = self._get_trace_from_exception(context.current_address, e)
            context.traces.append(trace)
            context.event_logs.clear()
            context.logs_bloom.value = 0
        finally:
            # Charge a fee to from account
            final_step_used, final_step_price =\
                self._charge_transaction_fee(
                    context,
                    params,
                    tx_result.status,
                    context.step_counter.step_used)

            # Finalize tx_result
            context.cumulative_step_used += final_step_used
            tx_result.step_used = final_step_used
            tx_result.cumulative_step_used = context.cumulative_step_used
            tx_result.event_logs = context.event_logs
            tx_result.logs_bloom = context.logs_bloom
            tx_result.traces = context.traces

        return tx_result

    def _get_byte_length(self, data) -> int:
        size = 0
        if data:
            if isinstance(data, dict):
                for v in data.values():
                    size += self._get_byte_length(v)
            elif isinstance(data, list):
                for v in data:
                    size += self._get_byte_length(v)
            elif isinstance(data, str):
                # If the value is hexstring, it is calculated as bytes otherwise
                # string
                data_body = data[2:] if data.startswith('0x') else data
                if is_lowercase_hex_string(data_body):
                    size += ceil(len(data_body) / 2)
                else:
                    size += len(data.encode('utf-8'))
            else:
                # int and bool
                if isinstance(data, int):
                    size += byte_length_of_int(data)
        return size

    def _transfer_coin(self,
                       context: 'IconScoreContext',
                       params: dict) -> None:
        """Transfer coin between EOA and EOA based on protocol v2
        JSON-RPC syntax validation has already been complete

        :param context:
        :param params:
        :return:
        """
        from_: 'Address' = params['from']
        to: 'Address' = params['to']
        value: int = params.get('value', 0)

        self._icx_engine.transfer(context, from_, to, value)

    def _charge_transaction_fee(self,
                                context: 'IconScoreContext',
                                params: dict,
                                status: int,
                                step_used: int) -> (int, int):
        """Charge a fee to from account
        Because it is on finalizing a transaction,
        this method MUST NOT throw any exceptions

        Assume that from account can charge a failed tx fee

        :param params:
        :param status: 1: SUCCESS, 0: FAILURE
        :return: final step_used, step_price
        """
        version: int = params.get('version', 2)
        from_: 'Address' = params['from']

        step_price = context.step_counter.step_price

        if version < 3:
            # Support coin transfer based on protocol v2
            # 0.01 icx == 10**16 loop
            # FIXED_FEE(0.01 icx) == step_used(10**4) * step_price(10**12)
            step_used = 10 ** 4

            if status == TransactionResult.FAILURE:
                # protocol v2 does not charge a fee for a failed tx
                step_price = 0
            elif self._is_flag_on(IconServiceFlag.ENABLE_FEE):
                # 0.01 icx == 10**16 loop
                # FIXED_FEE(0.01 icx) == step_used(10**4) * step_price(10**12)
                step_price = 10 ** 12

        # Charge a fee to from account
        fee: int = step_used * step_price
        self._icx_engine.charge_fee(context, from_, fee)

        # final step_used and step_price
        return step_used, step_price

    def _get_step_price(self):
        """
        Gets the step price
        :return: step price in loop unit
        """
        return self._step_counter_factory.get_step_price()

    def _handle_score_invoke(self,
                             context: 'IconScoreContext',
                             to: 'Address',
                             params: dict) -> Optional['Address']:
        """Handle score invocation

        :param context:
        :param to: a recipient address
        :param params:
        :return: SCORE address if 'deploy' command. otherwise None
        """
        data_type: str = params.get('dataType')
        data: dict = params.get('data')

        if data_type == 'deploy':
            if to == ZERO_SCORE_ADDRESS:
                # SCORE install
                content_type = data.get('contentType')

                if content_type == 'application/tbears':
                    path: str = data.get('content')
                    score_address = _generate_score_address_for_tbears(path)
                else:
                    score_address = _generate_score_address(
                        context.tx.origin,
                        context.tx.timestamp,
                        context.tx.nonce)
                context.step_counter.apply_step(StepType.CONTRACT_CREATE, 1)
            else:
                # SCORE update
                score_address = to
                context.step_counter.apply_step(StepType.CONTRACT_UPDATE, 1)

            data_size = self._get_byte_length(data.get('content', None))
            context.step_counter.apply_step(StepType.CONTRACT_SET, data_size)

            self._icon_score_deploy_engine.invoke(
                context=context,
                to=to,
                icon_score_address=score_address,
                data=data)
            return score_address
        else:
            context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
            self._icon_score_engine.invoke(context, to, data_type, data)
            return None

    @staticmethod
    def _get_failure_from_exception(
            e: BaseException) -> TransactionResult.Failure:
        """
        Gets `Failure` from an exception
        :param e: exception
        :return: a Failure
        """

        if isinstance(e, IconServiceBaseException):
            Logger.exception(e.message, ICON_SERVICE_LOG_TAG)
            code = e.code
            message = e.message
        else:
            Logger.exception(e, ICON_SERVICE_LOG_TAG)
            code = ExceptionCode.SERVER_ERROR
            message = str(e)

        return TransactionResult.Failure(code, message)

    @staticmethod
    def _get_trace_from_exception(address: 'Address', e: BaseException):
        """
        Gets trace from an exception
        :param address: The SCORE address the exception is thrown
        :param e: exception
        :return: a Trace
        """
        return Trace(
            address,
            TraceType.REVERT if isinstance(e, RevertException) else
            TraceType.THROW,
            [e.code, e.message] if isinstance(e, IconServiceBaseException) else
            [ExceptionCode.SERVER_ERROR, str(e)]
        )

    def _handle_icx_get_score_api(self,
                                  context: 'IconScoreContext',
                                  params: dict) -> object:
        """Handles an icx_get_score_api jsonrpc request

        get score api

        :param context:
        :param params:
        :return:
        """
        icon_score_address: Address = params['address']
        return self._icon_score_engine.get_score_api(context, icon_score_address)

    def commit(self) -> None:
        """Write updated states in a context.block_batch to StateDB
        when the candidate block has been confirmed
        """
        if self._precommit_state is None:
            raise ServerErrorException(
                'Precommit state is none on commit')

        context = self._context_factory.create(IconScoreContextType.DIRECT)
        block_batch = self._precommit_state.block_batch

        for address in block_batch:
            if address == ICX_ENGINE_ADDRESS:
                context_db = self._icx_context_db
            else:
                icon_score = self._icon_score_mapper.get_icon_score(context, address)
                context_db = icon_score.db._context_db

            context_db.write_batch(context=None, states=block_batch[address])

        self._icon_score_engine.commit(context)
        self._icon_score_deploy_engine.commit(context)
        self._precommit_state = None

        self._icx_storage.put_block_info(context, block_batch.block)
        self._context_factory.destroy(context)

    def validate_precommit(self, precommit_block: 'Block') -> None:
        if self._precommit_state is None:
            raise ServerErrorException('precommit_state is None')

        block = self._precommit_state.block_batch.block

        if block.hash != precommit_block.hash\
                or block.height != precommit_block.height:
            raise ServerErrorException(
                f'block({block.height}, {block.hash.hex()}) != '
                f'precommit block({precommit_block.height}, '
                f'{precommit_block.hash.hex()})')

    def rollback(self) -> None:
        """Throw away a precommit state
        in context.block_batch and IconScoreEngine
        """
        self._precommit_state = None
        self._icon_score_engine.rollback()
        self._icon_score_deploy_engine.rollback()
