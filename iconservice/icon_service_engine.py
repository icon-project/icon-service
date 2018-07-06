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
from os import makedirs
from typing import TYPE_CHECKING, Any, List, Optional

from iconservice.utils.bloom import BloomFilter
from .base.address import Address, AddressPrefix
from .base.address import ICX_ENGINE_ADDRESS, ZERO_SCORE_ADDRESS
from .base.block import Block
from .base.exception import ExceptionCode, RevertException
from .base.exception import IconServiceBaseException, ServerErrorException
from .base.message import Message
from .base.transaction import Transaction
from .database.batch import BlockBatch, TransactionBatch
from .database.factory import DatabaseFactory
from .deploy.icon_score_deploy_engine import IconScoreDeployEngine
from .icon_config import *
from .iconscore.icon_pre_validator import IconPreValidator
from .iconscore.icon_score_context import IconScoreContext
from .iconscore.icon_score_context import IconScoreContextFactory
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .iconscore.icon_score_loader import IconScoreLoader
from .iconscore.icon_score_result import TransactionResult
from .iconscore.icon_score_step import IconScoreStepCounterFactory, StepType
from .icx.icx_account import AccountType
from .icx.icx_engine import IcxEngine
from .icx.icx_storage import IcxStorage
from .iconscore.icon_score_trace import Trace, TraceType
from .logger import Logger

if TYPE_CHECKING:
    from .iconscore.icon_score_step import IconScoreStepCounter
    from .iconscore.icon_score_event_log import EventLog


def _generate_score_address_for_tbears(path: str) -> 'Address':
    """

    :param path: The path of a SCORE which is under development with tbears
    :return:
    """
    project_name = path.split('/')[-1]
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
    data = from_.body + timestamp.to_bytes(32, 'big')
    if nonce:
        data += nonce.to_bytes(32, 'big')

    return Address.from_data(AddressPrefix.CONTRACT, data)


class IconServiceEngine(object):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconOuterService.
    """

    def __init__(self) -> None:
        """Constructor
        """

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

        # jsonrpc handlers
        self._handlers = {
            'icx_getBalance': self._handle_icx_get_balance,
            'icx_getTotalSupply': self._handle_icx_get_total_supply,
            'icx_call': self._handle_icx_call,
            'icx_sendTransaction': self._handle_icx_send_transaction,
            'icx_getScoreApi': self._handle_icx_get_score_api
        }

        # The precommit state is the state that been already invoked,
        # but not written to levelDB or file system.
        self._PrecommitState = namedtuple(
            'PrecommitState', ['block_batch', 'block_result'])

    def open(self,
             icon_score_root_path: str,
             state_db_root_path: str) -> None:
        """Get necessary parameters and initialize diverse objects

        :param icon_score_root_path:
        :param state_db_root_path:
        """

        makedirs(icon_score_root_path, exist_ok=True)
        makedirs(state_db_root_path, exist_ok=True)

        self._db_factory = DatabaseFactory(state_db_root_path)
        self._context_factory = IconScoreContextFactory(max_size=5)
        self._icon_score_loader = IconScoreLoader(icon_score_root_path)

        self._icx_context_db = self._db_factory.create_by_name(ICON_DEX_DB_NAME)
        self._icx_context_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_context_db)

        self._icx_engine = IcxEngine()
        self._icx_engine.open(self._icx_storage)

        self._icon_score_mapper = IconScoreInfoMapper(
            self._icx_storage, self._db_factory, self._icon_score_loader)

        self._icon_score_engine = IconScoreEngine(
            self._icx_storage, self._icon_score_mapper)

        icon_score_deploy_engine_flags = \
            IconScoreDeployEngine.Flag.ENABLE_DEPLOY_AUDIT
        self._icon_score_deploy_engine = IconScoreDeployEngine(
            icon_score_root_path=icon_score_root_path,
            flags=icon_score_deploy_engine_flags,
            context_db=self._icx_context_db,
            icx_storage=self._icx_storage,
            icon_score_mapper=self._icon_score_mapper)

        self._step_counter_factory = IconScoreStepCounterFactory()
        self._step_counter_factory.set_step_unit(StepType.TRANSACTION, 6000)
        self._step_counter_factory.set_step_unit(StepType.STORAGE_SET, 200)
        self._step_counter_factory.set_step_unit(StepType.STORAGE_REPLACE, 50)
        self._step_counter_factory.set_step_unit(StepType.STORAGE_DELETE, -100)
        self._step_counter_factory.set_step_unit(StepType.TRANSFER, 10000)
        self._step_counter_factory.set_step_unit(StepType.CALL, 1000)
        self._step_counter_factory.set_step_unit(StepType.EVENTLOG, 20)

        self._icon_pre_validator = IconPreValidator(icx=self._icx_engine)

        IconScoreContext.icx = self._icx_engine
        IconScoreContext.icon_score_mapper = self._icon_score_mapper

    def close(self) -> None:
        """Free all resources occupied by IconServiceEngine
        including db, memory and so on
        """

        self._icx_engine.close()

    def invoke(self,
               block: 'Block',
               tx_params: list) -> tuple:
        """Process transactions in a block sent by loopchain

        :param block:
        :param tx_params: transactions in a block
        :return: (TransactionResult[], bytes)
        """
        context = self._context_factory.create(IconScoreContextType.INVOKE)
        context.block = block
        context.block_batch = BlockBatch(Block.from_block(block))
        context.tx_batch = TransactionBatch()
        block_result = []

        for index, tx in enumerate(tx_params):
            if self._is_genesis_block(index, block.height, tx):
                tx_result = self._invoke_genesis(context, tx, index)
            else:
                tx_result = self._invoke(context, tx, index)
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
            raise ServerErrorException(f'NextBlockHeight[{block.height}] '
                                       f'is not LastBlockHeight[{last_block.height}] + 1')
        elif block.prev_hash != last_block.hash:
            raise ServerErrorException(f'NextBlock.prevHash[{block.prev_hash}] '
                                       f'is not LastBlockHash[{last_block.hash}]')

    @staticmethod
    def _is_genesis_block(index: int, block_height: int, tx_params: dict) -> bool:
        if block_height != 0 or index != 0:
            return False

        return 'genesisData' in tx_params

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

        tx_result = TransactionResult(
            context.tx.hash, context.block, context.tx.index)

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

    def _invoke(self,
                context: 'IconScoreContext',
                tx_params: dict,
                index: int) -> 'TransactionResult':

        method = tx_params['method']
        params = tx_params['params']
        addr_from = params['from']
        addr_to = params['to']

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=index,
                                 origin=addr_from,
                                 timestamp=params['timestamp'],
                                 nonce=params.get('nonce', None))

        context.msg = Message(sender=addr_from, value=params.get('value', 0))
        context.current_address = addr_to
        context.event_logs: List['EventLog'] = []
        context.logs_bloom: BloomFilter = BloomFilter()
        context.traces: List['Trace'] = []
        context.step_counter: IconScoreStepCounter = \
            self._step_counter_factory.create(
                params.get('stepLimit', ICON_SERVICE_BIG_STEP_LIMIT)
            )
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

    def validate_for_invoke(self, tx: dict) -> None:
        """Validate a transaction before putting it into tx pool.
        If failed to validate a tx, client will get a json-rpc error response

        :param tx: dict including tx info
        """

        # FIXME: If step_price is defined, it should be updated.
        context = self._context_factory.create(IconScoreContextType.QUERY)
        self._icon_pre_validator.validate_tx(context, tx, step_price=0)
        self._context_factory.destroy(context)

    def validate_for_query(self, request: dict) -> None:
        self._icon_pre_validator.validate_query(request)

    def _call(self,
              context: 'IconScoreContext',
              method: str,
              params: dict) -> Any:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have been already converted to the proper types.
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
        handler = self._handlers[method]
        return handler(context, params)

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

        :param params: jsonrpc params
        :return: return value of an IconScoreBase method
            None is allowed
        """
        tx_result = TransactionResult(
            context.tx.hash, context.block, context.tx.index)

        try:
            # all transactions have 'to' field.
            to: Address = params['to']
            tx_result.to = to

            _from: Address = params['from']
            value: int = params.get('value', 0)

            self._icx_engine.transfer(context, _from, to, value)

            if to.is_contract:
                data_type: str = params.get('dataType')
                data: dict = params.get('data')

                tx_result.score_address = \
                    self._handle_score_invoke(context, to, data_type, data)

            tx_result.status = TransactionResult.SUCCESS
        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)
            trace = self._get_trace_from_exception(context.current_address, e)
            context.traces.append(trace)
            context.event_logs.clear()
            context.logs_bloom.value = 0
        finally:
            tx_result.step_used = context.step_counter.step_used
            tx_result.event_logs = context.event_logs
            tx_result.logs_bloom = context.logs_bloom
            # tx_result.traces = context.traces

        return tx_result

    def _handle_score_invoke(self,
                             context: 'IconScoreContext',
                             to: 'Address',
                             data_type: str,
                             data: dict,) -> Optional['Address']:
        """Handle score invocation

        :param context:
        :param to: a recipient address
        :param data_type:
        :param data:
        :return: SCORE address if 'deploy' command. otherwise None
        """
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
            else:
                # SCORE update
                score_address = to

            self._icon_score_deploy_engine.invoke(
                context=context,
                to=to,
                icon_score_address=score_address,
                data=data)
            return score_address
        else:
            self._icon_score_engine.invoke(
                context, to, data_type, data)
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
            [e.code, e.message]
        )

    def _handle_icx_get_score_api(self,
                                  context: 'IconScoreContext',
                                  params: dict) -> object:
        """Handles an icx_get_score_api jsonrpc request

        get score api

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

        context = self._context_factory.create(IconScoreContextType.GENESIS)
        block_batch = self._precommit_state.block_batch

        for address in block_batch:
            if address == ICX_ENGINE_ADDRESS:
                context_db = self._icx_context_db
            else:
                icon_score = self._icon_score_mapper.get_icon_score(address)
                context_db = icon_score.db._context_db

            context_db.write_batch(context=None, states=block_batch[address])

        self._icon_score_engine.commit(context)
        self._icon_score_deploy_engine.commit(context)
        self._precommit_state = None

        self._icx_storage.put_block_info(context, block_batch.block)
        self._context_factory.destroy(context)

    def validate_precommit(self, precommit_block: 'Block') -> None:
        if self._precommit_state is None:
            raise ServerErrorException('_precommit_state is None')

        block = self._precommit_state.block_batch.block

        is_match = block.hash == precommit_block.hash and block.height == precommit_block.height
        if not is_match:
            raise ServerErrorException('mismatch block')

    def rollback(self) -> None:
        """Throw away a precommit state
        in context.block_batch and IconScoreEngine
        """
        self._precommit_state = None
        self._icon_score_engine.rollback()
        self._icon_score_deploy_engine.rollback()
