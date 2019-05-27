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

import os
from typing import TYPE_CHECKING, List, Any, Optional

from iconcommons.logger import Logger
from .base.address import Address, generate_score_address, generate_score_address_for_tbears
from .base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from .base.block import Block
from .base.exception import ExceptionCode, IconServiceBaseException, ScoreNotFoundException, \
    AccessDeniedException, IconScoreException
from .base.message import Message
from .base.transaction import Transaction
from .database.batch import BlockBatch, TransactionBatch
from .database.factory import ContextDatabaseFactory
from .deploy.icon_builtin_score_loader import IconBuiltinScoreLoader
from .deploy.icon_score_deploy_engine import IconScoreDeployEngine
from .deploy.icon_score_deploy_storage import IconScoreDeployStorage
from .fee.fee_engine import FeeEngine, DepositHandler
from .fee.fee_storage import FeeStorage
from .icon_constant import ICON_DEX_DB_NAME, ICON_SERVICE_LOG_TAG, IconServiceFlag, ConfigKey, \
    REVISION_3
from .iconscore.icon_pre_validator import IconPreValidator
from .iconscore.icon_score_class_loader import IconScoreClassLoader
from .iconscore.icon_score_context import IconScoreContext, IconScoreFuncType, ContextContainer
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_context_util import IconScoreContextUtil
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_event_log import EventLogEmitter
from .iconscore.icon_score_mapper import IconScoreMapper
from .iconscore.icon_score_result import TransactionResult
from .iconscore.icon_score_step import IconScoreStepCounterFactory, StepType, get_input_data_size, \
    get_deploy_content_size
from .iconscore.icon_score_trace import Trace, TraceType
from .icx.icx_account import AccountType
from .icx.icx_engine import IcxEngine
from .icx.icx_storage import IcxStorage
from .precommit_data_manager import PrecommitData, PrecommitDataManager, PrecommitFlag
from .utils import sha3_256, int_to_bytes
from .utils import to_camel_case
from .utils.bloom import BloomFilter

if TYPE_CHECKING:
    from .iconscore.icon_score_event_log import EventLog
    from .builtin_scores.governance.governance import Governance
    from iconcommons.icon_config import IconConfig


class IconServiceEngine(ContextContainer):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconInnerService.
    """

    def __init__(self) -> None:
        """Constructor

        """
        self._conf = None
        self._icx_context_db = None
        self._icx_storage = None
        self._icx_engine = None
        self._icon_score_deploy_engine = None
        self._step_counter_factory = None
        self._icon_pre_validator = None
        self._fee_storage = None
        self._fee_engine = None
        self._deposit_handler = None

        # JSON-RPC handlers
        self._handlers = {
            'icx_getBalance': self._handle_icx_get_balance,
            'icx_getTotalSupply': self._handle_icx_get_total_supply,
            'icx_call': self._handle_icx_call,
            'icx_sendTransaction': self._handle_icx_send_transaction,
            'debug_estimateStep': self._handle_estimate_step,
            'icx_getScoreApi': self._handle_icx_get_score_api,
            'ise_getStatus': self._handle_ise_get_status
        }

        self._precommit_data_manager = PrecommitDataManager()

    def open(self, conf: 'IconConfig') -> None:
        """Get necessary parameters and initialize diverse objects

        :param conf:
        """

        self._conf = conf
        service_config_flag = self._make_service_flag(self._conf[ConfigKey.SERVICE])
        score_root_path: str = self._conf[ConfigKey.SCORE_ROOT_PATH].rstrip('/')
        score_root_path = os.path.abspath(score_root_path)
        state_db_root_path: str = self._conf[ConfigKey.STATE_DB_ROOT_PATH].rstrip('/')

        os.makedirs(score_root_path, exist_ok=True)
        os.makedirs(state_db_root_path, exist_ok=True)

        # Share one context db with all SCOREs
        ContextDatabaseFactory.open(
            state_db_root_path, ContextDatabaseFactory.Mode.SINGLE_DB)

        self._icx_engine = IcxEngine()
        self._icon_score_deploy_engine = IconScoreDeployEngine()

        self._icx_context_db = ContextDatabaseFactory.create_by_name(ICON_DEX_DB_NAME)
        self._icx_storage = IcxStorage(self._icx_context_db)
        self._fee_storage = FeeStorage(self._icx_context_db)
        icon_score_deploy_storage = IconScoreDeployStorage(self._icx_context_db)

        self._step_counter_factory = IconScoreStepCounterFactory()
        self._fee_engine = FeeEngine(
            icon_score_deploy_storage, self._fee_storage, self._icx_storage, self._icx_engine)
        self._deposit_handler = DepositHandler(self._fee_engine)
        self._icon_pre_validator = \
            IconPreValidator(self._icx_engine, self._fee_engine, icon_score_deploy_storage)

        IconScoreClassLoader.init(score_root_path)
        IconScoreContext.score_root_path = score_root_path
        IconScoreContext.icx_engine = self._icx_engine
        IconScoreContext.fee_engine = self._fee_engine
        IconScoreContext.icon_score_mapper = IconScoreMapper(is_threadsafe=True)
        IconScoreContext.icon_score_deploy_engine = self._icon_score_deploy_engine
        IconScoreContext.icon_service_flag = service_config_flag
        IconScoreContext.legacy_tbears_mode = self._conf.get(ConfigKey.TBEARS_MODE, False)

        self._icx_engine.open(self._icx_storage)
        self._icon_score_deploy_engine.open(icon_score_deploy_storage)

        self._load_builtin_scores()
        self._init_global_value_by_governance_score()

        self._precommit_data_manager.last_block = self._icx_storage.last_block

    @staticmethod
    def _make_service_flag(flag_table: dict) -> int:
        make_flag = 0
        for flag in IconServiceFlag:
            flag_name = to_camel_case(flag.name.lower())
            is_enable = flag_table.get(flag_name, False)
            if is_enable:
                make_flag |= flag
        return make_flag

    def _load_builtin_scores(self):
        context = IconScoreContext(IconScoreContextType.DIRECT)
        try:
            self._push_context(context)
            IconBuiltinScoreLoader.load_builtin_scores(
                context, self._conf[ConfigKey.BUILTIN_SCORE_OWNER])
        finally:
            self._pop_context()

    def _init_global_value_by_governance_score(self):
        """Initialize step_counter_factory with parameters
        managed by governance SCORE

        :return:
        """
        context = IconScoreContext(IconScoreContextType.QUERY)
        # Clarifies this context does not count steps
        context.step_counter = None

        try:
            self._push_context(context)
            # Gets the governance SCORE
            governance_score = self._get_governance_score(context)

            step_price = self._get_step_price_from_governance(context, governance_score)
            step_costs = self._get_step_costs_from_governance(governance_score)
            max_step_limits = self._get_step_max_limits_from_governance(governance_score)

            # Keep properties into the counter factory
            self._step_counter_factory.set_step_properties(
                step_price, step_costs, max_step_limits)

        finally:
            self._pop_context()

    def _set_revision_to_context(self, context):
        try:
            self._push_context(context)
            governance_score = self._get_governance_score(context)
            if hasattr(governance_score, 'revision_code'):
                context.revision = governance_score.revision_code
        finally:
            self._pop_context()

    @staticmethod
    def _get_governance_score(context) -> 'Governance':
        governance_score: 'Governance' = IconScoreContextUtil.get_icon_score(
            context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ScoreNotFoundException('Governance SCORE not found')
        return governance_score

    @staticmethod
    def _get_step_price_from_governance(context: 'IconScoreContext', governance) -> int:
        step_price = 0
        # Gets the step price if the fee flag is on
        if IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.FEE):
            step_price = governance.getStepPrice()

        return step_price

    @staticmethod
    def _get_step_costs_from_governance(governance) -> dict:
        step_costs = {}
        # Gets the step costs
        for key, value in governance.getStepCosts().items():
            try:
                step_costs[StepType(key)] = value
            except ValueError:
                # Pass the unknown step type
                pass

        return step_costs

    @staticmethod
    def _get_step_max_limits_from_governance(governance) -> dict:
        # Gets the max step limit
        return {IconScoreContextType.INVOKE: governance.getMaxStepLimit("invoke"),
                IconScoreContextType.QUERY: governance.getMaxStepLimit("query")}

    def _validate_deployer_whitelist(
            self, context: 'IconScoreContext', params: dict):
        data_type = params.get('dataType')

        if data_type != 'deploy':
            return

        _from: 'Address' = params.get('from')
        if _from is None:
            return

        try:
            self._push_context(context)
            # Gets the governance SCORE
            governance_score = self._get_governance_score(context)

            if not governance_score.isDeployer(_from):
                raise AccessDeniedException(f'Invalid deployer: no permission ({_from})')
        finally:
            self._pop_context()

    def close(self) -> None:
        """Free all resources occupied by IconServiceEngine
        including db, memory and so on
        """
        context = IconScoreContext(IconScoreContextType.DIRECT)
        try:
            self._push_context(context)
            self._icx_engine.close()

            IconScoreContext.icon_score_mapper.close()
            IconScoreContext.icon_score_mapper = None

            IconScoreClassLoader.exit(context.score_root_path)
        finally:
            self._pop_context()
            ContextDatabaseFactory.close()
            self._clear_context()

    def invoke(self,
               block: 'Block',
               tx_requests: list) -> tuple:
        """Process transactions in a block sent by loopchain

        :param block:
        :param tx_requests: transactions in a block
        :return: (TransactionResult[], bytes)
        """
        # If the block has already been processed,
        # return the result from PrecommitDataManager
        precommit_data: 'PrecommitData' = self._precommit_data_manager.get(block.hash)
        if precommit_data is not None:
            Logger.info(
                f'The result of block(0x{block.hash.hex()} already exists',
                ICON_SERVICE_LOG_TAG)
            return precommit_data.block_result, precommit_data.state_root_hash

        # Check for block validation before invoke
        self._precommit_data_manager.validate_block_to_invoke(block)

        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.step_counter = self._step_counter_factory.create(IconScoreContextType.INVOKE)
        context.block = block
        context.block_batch = BlockBatch(Block.from_block(block))
        context.tx_batch = TransactionBatch()
        context.new_icon_score_mapper = IconScoreMapper()
        self._set_revision_to_context(context)
        block_result = []
        precommit_flag = PrecommitFlag.NONE

        if block.height == 0:
            # Assume that there is only one tx in genesis_block
            tx_result = self._invoke_genesis(context, tx_requests[0], 0)
            block_result.append(tx_result)
            context.block_batch.update(context.tx_batch)
            context.tx_batch.clear()
        else:
            for index, tx_request in enumerate(tx_requests):
                tx_result = self._invoke_request(context, tx_request, index)
                block_result.append(tx_result)
                context.block_batch.update(context.tx_batch)
                context.tx_batch.clear()
                self._update_revision_if_necessary(context, tx_result)
                tx_precommit_flag = self._generate_precommit_flag(tx_result)
                self._update_step_properties_if_necessary(context, tx_precommit_flag)
                precommit_flag |= tx_precommit_flag

        # Save precommit data
        # It will be written to levelDB on commit
        precommit_data = PrecommitData(
            context.block_batch, block_result, context.new_icon_score_mapper, precommit_flag)
        self._precommit_data_manager.push(precommit_data)

        return block_result, precommit_data.state_root_hash

    def _update_revision_if_necessary(self, context, tx_result):
        """
        Updates the revision code of given context if governance or its states has been updated
        :param context: current context
        :param tx_result: transaction result
        :return:
        """
        if tx_result.to == GOVERNANCE_SCORE_ADDRESS and \
                tx_result.status == TransactionResult.SUCCESS:
            # If the tx is heading for Governance, updates the revision
            self._set_revision_to_context(context)

    @staticmethod
    def _generate_precommit_flag(tx_result) -> PrecommitFlag:
        """
        Generates pre-commit flag related in STEP properties from the transaction result

        :param tx_result: transaction result
        :return: pre-commit flag related in STEP properties
        """
        precommit_flag = PrecommitFlag.NONE

        if tx_result.to == GOVERNANCE_SCORE_ADDRESS and \
                tx_result.status == TransactionResult.SUCCESS:
            precommit_flag = PrecommitFlag.STEP_ALL_CHANGED

        return precommit_flag

    def _update_step_properties_if_necessary(self, context, precommit_flag):
        """
        Updates step properties to the step counter if the pre-commit flag is set

        :param context: current context
        :param precommit_flag: pre-commit flag
        """
        if precommit_flag & PrecommitFlag.STEP_ALL_CHANGED == PrecommitFlag.NONE:
            return

        try:
            self._push_context(context)
            governance_score = self._get_governance_score(context)

            step_price: int = self._get_step_price_from_governance(context, governance_score)
            context.step_counter.set_step_price(step_price)

            step_costs: dict = self._get_step_costs_from_governance(governance_score)
            context.step_counter.set_step_costs(step_costs)

            max_step_limits: dict = self._get_step_max_limits_from_governance(governance_score)
            context.step_counter.set_max_step_limit(max_step_limits.get(context.type, 0))
        finally:
            self._pop_context()

    @staticmethod
    def _is_genesis_block(
            tx_index: int, block_height: int, tx_params: dict) -> bool:

        return block_height == 0 \
               and tx_index == 0 \
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

        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)

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

        # If the request is V2 the stepLimit field is not there,
        # so fills it as the max step limit to proceed the transaction.
        step_limit: int = params.get('stepLimit', context.step_counter.max_step_limit)

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=index,
                                 origin=from_,
                                 to=to,
                                 timestamp=params.get('timestamp', context.block.timestamp),
                                 nonce=params.get('nonce', None))

        context.msg = Message(sender=from_, value=params.get('value', 0))
        context.current_address = to
        context.event_logs: List['EventLog'] = []
        context.traces: List['Trace'] = []
        context.step_counter.reset(step_limit)
        context.msg_stack.clear()
        context.event_log_stack.clear()
        context.fee_sharing_proportion = 0

        return self._call(context, method, params)

    def _estimate_step_by_request(self, request, context) -> int:
        """Calculates simply and estimates step with request data.

        :param request:
        :param context:
        """
        params: dict = request['params']
        data_type: str = params.get('dataType')
        data: dict = params.get('data')
        to: Address = params['to']

        context.step_counter.apply_step(StepType.DEFAULT, 1)

        input_size = get_input_data_size(context.revision, data)
        context.step_counter.apply_step(StepType.INPUT, input_size)

        if data_type == "deploy":
            content_size = get_deploy_content_size(context.revision, data.get('content', None))
            context.step_counter.apply_step(StepType.CONTRACT_SET, content_size)
            # When installing SCORE.
            if to == ZERO_SCORE_ADDRESS:
                context.step_counter.apply_step(StepType.CONTRACT_CREATE, 1)
            # When updating SCORE.
            else:
                context.step_counter.apply_step(StepType.CONTRACT_UPDATE, 1)

        return context.step_counter.step_used

    def _estimate_step_by_execution(self, request, context, step_limit) -> int:
        """Processes the transaction and estimates step.

        :param request:
        :param context:
        :param step_limit:
        """
        method: str = request['method']
        params: dict = request['params']

        from_: Address = params['from']
        to: Address = params['to']

        timestamp = params.get('timestamp', self._icx_storage.last_block.timestamp)
        context.tx = Transaction(tx_hash=sha3_256(int_to_bytes(timestamp)),
                                 index=0,
                                 origin=from_,
                                 timestamp=timestamp,
                                 nonce=params.get('nonce', None))
        context.msg = Message(sender=from_, value=params.get('value', 0))
        context.current_address = to
        context.event_logs: List['EventLog'] = []
        context.traces: List['Trace'] = []

        # Deposits virtual ICXs to the sender to prevent validation error due to 'out of balance'.
        account = self._icx_storage.get_account(context, from_)
        account.deposit(step_limit * context.step_counter.step_price + params.get('value', 0))
        self._icx_storage.put_account(context, from_, account)
        return self._call(context, method, params)

    def estimate_step(self, request: dict) -> int:
        """
        Estimates the amount of step to process a specific transaction.

        [Specific information of each step]
        1. Transfer coin
            1) When the destination is EOA: Default
            2) when the destination is SCORE: process and estimate steps without commit
        2. Deploy
            1) Installing SCORE: Default + INPUT + CONTRACT_CREATE + CONTRACT_SET
            2) Update SCORE: Default + INPUT + CONTRACT_UPDATE + CONTRACT_SET
        3. Call
            - process and estimate steps without commit
        4. Message
            1) When the destination is EOA: Default + INPUT
            2) when the destination is SCORE: process and estimate steps without commit

        :return: The amount of step
        """
        context = IconScoreContext(IconScoreContextType.ESTIMATION)
        context.step_counter = self._step_counter_factory.create(IconScoreContextType.INVOKE)
        context.block = self._precommit_data_manager.last_block
        context.block_batch = BlockBatch(Block.from_block(context.block))
        context.tx_batch = TransactionBatch()
        context.new_icon_score_mapper = IconScoreMapper()
        self._set_revision_to_context(context)
        # Fills the step_limit as the max step limit to proceed the transaction.
        step_limit: int = context.step_counter.max_step_limit
        context.step_counter.reset(step_limit)

        params: dict = request['params']
        data_type: str = params.get('dataType')
        to: Address = params['to']

        if data_type == "deploy" or not to.is_contract:
            # Calculates simply and estimates step with request data.
            return self._estimate_step_by_request(request, context)
        else:
            # Processes the transaction and estimates step.
            return self._estimate_step_by_execution(request, context, step_limit)

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
        context = IconScoreContext(IconScoreContextType.QUERY)
        context.block = self._icx_storage.last_block
        context.step_counter = self._step_counter_factory.create(IconScoreContextType.QUERY)
        self._set_revision_to_context(context)
        step_limit: int = context.step_counter.max_step_limit

        if params:
            from_: 'Address' = params.get('from', None)
            context.msg = Message(sender=from_)
            step_limit: int = params.get('stepLimit', step_limit)

        context.traces: List['Trace'] = []
        context.step_counter.reset(step_limit)

        ret = self._call(context, method, params)

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
        assert self._get_context_stack_size() == 0

        method = request['method']
        assert method in ('icx_sendTransaction', 'debug_estimateStep')
        assert 'params' in request

        params: dict = request['params']
        to: 'Address' = params.get('to')

        context = IconScoreContext(IconScoreContextType.QUERY)
        context.block = self._icx_storage.last_block
        context.step_counter = self._step_counter_factory.create(IconScoreContextType.QUERY)
        self._set_revision_to_context(context)

        try:
            self._push_context(context)

            step_price: int = context.step_counter.step_price
            minimum_step: int = self._step_counter_factory.get_step_cost(StepType.DEFAULT)

            if 'data' in params:
                # minimum_step is the sum of
                # default STEP cost and input STEP costs if data field exists
                data = params['data']
                input_size = get_input_data_size(context.revision, data)
                minimum_step += input_size * self._step_counter_factory.get_step_cost(StepType.INPUT)

            self._icon_pre_validator.execute(context, params, step_price, minimum_step)

            IconScoreContextUtil.validate_score_blacklist(context, to)
            if IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.DEPLOYER_WHITE_LIST):
                self._validate_deployer_whitelist(context, params)
        finally:
            self._pop_context()

    def _call(self,
              context: 'IconScoreContext',
              method: str,
              params: dict) -> Any:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that
        all param values have already been converted to the proper types.
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
        assert self._get_context_stack_size() == 0

        try:
            self._push_context(context)

            handler = self._handlers[method]
            ret = handler(context, params)
        finally:
            self._pop_context()

        return ret

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

        context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)

        return IconScoreEngine.query(context, icon_score_address, data_type, data)

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
            tx_result.to = params['to']

            # process the transaction
            score_address = self._process_transaction(context, params)

            tx_result.score_address = score_address
            tx_result.status = TransactionResult.SUCCESS
        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)
            trace = self._get_trace_from_exception(context.current_address, e)
            context.tx_batch.clear()
            context.traces.append(trace)
            context.event_logs.clear()
        finally:
            # Revert func_type to IconScoreFuncType.WRITABLE
            # to avoid DatabaseException in self._charge_transaction_fee()
            context.func_type = IconScoreFuncType.WRITABLE

            # Charge a fee to from account
            step_used_details, final_step_price = \
                self._charge_transaction_fee(
                    context,
                    params,
                    tx_result.status,
                    context.step_counter.step_used)

            # Finalize tx_result
            tx_result.step_price = final_step_price
            tx_result.event_logs = context.event_logs
            tx_result.logs_bloom = self._generate_logs_bloom(context.event_logs)
            tx_result.traces = context.traces
            final_step_used = self._append_step_results(tx_result, context, step_used_details)

            context.cumulative_step_used += final_step_used

        return tx_result

    def _handle_estimate_step(self,
                              context: 'IconScoreContext',
                              params: dict) -> int:
        """
        Handles estimate step by execution of tx

        :param context: context
        :param params: parameters of tx
        :return: estimated steps
        """

        self._process_transaction(context, params)

        return context.step_counter.step_used

    def _process_transaction(self,
                             context: 'IconScoreContext',
                             params: dict) -> Optional['Address']:
        """
        Processes the transaction

        :param params: JSON-RPC params
        :return: SCORE address if 'deploy' command. otherwise None
        """

        to: Address = params['to']

        # Checks the balance only on the invoke context(skip estimate context)
        if context.type == IconScoreContextType.INVOKE:
            tmp_context = IconScoreContext(IconScoreContextType.QUERY)
            tmp_context.block = self._get_last_block()

            # Check if from account can charge a tx fee
            self._icon_pre_validator.execute_to_check_out_of_balance(
                context if context.revision >= REVISION_3 else tmp_context,
                params,
                context.step_counter.step_price)

        # Every send_transaction are calculated DEFAULT STEP at first
        context.step_counter.apply_step(StepType.DEFAULT, 1)

        input_size = get_input_data_size(context.revision, params.get('data', None))
        context.step_counter.apply_step(StepType.INPUT, input_size)

        data_type: str = params.get('dataType')
        if data_type in (None, 'call', 'message'):
            self._transfer_coin(context, params)

        score_address = None
        if to.is_contract:
            score_address = self._handle_score_invoke(context, to, params)

        return score_address

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
                                step_used: int) -> (dict, int):
        """Charge a fee to from account
        Because it is on finalizing a transaction,
        this method MUST NOT throw any exceptions

        Assume that from account can charge a failed tx fee

        :param params:
        :param status: 1: SUCCESS, 0: FAILURE
        :return: detail step usage, final step price
        """
        version: int = params.get('version', 2)
        from_: 'Address' = params['from']
        to: 'Address' = params['to']

        step_price = context.step_counter.step_price

        if version < 3:
            # Support coin transfer based on protocol v2
            # 0.01 icx == 10**16 loop
            # FIXED_FEE(0.01 icx) == step_used(10**6) * step_price(10**10)
            step_used = 10 ** 6

            if status == TransactionResult.FAILURE:
                # protocol v2 does not charge a fee for a failed tx
                step_price = 0
            elif IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.FEE):
                # 0.01 icx == 10**16 loop
                # FIXED_FEE(0.01 icx) == step_used(10**6) * step_price(10**10)
                step_price = 10 ** 10

        # Charge a fee to from account
        try:
            step_used_details = self._fee_engine.charge_transaction_fee(
                context, from_, to, step_price, step_used, context.block.height)
        except BaseException as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = str(e)
            Logger.exception(message, ICON_SERVICE_LOG_TAG)
            step_used_details = {from_: 0, to: 0}

        # final step_used and step_price
        return step_used_details, step_price

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
                    score_address = generate_score_address_for_tbears(path)
                else:
                    score_address = generate_score_address(
                        context.tx.origin,
                        context.tx.timestamp,
                        context.tx.nonce)
                    deploy_info = IconScoreContextUtil.get_deploy_info(context, score_address)
                    if deploy_info is not None:
                        raise AccessDeniedException(f'SCORE address already in use: {score_address}')
                context.step_counter.apply_step(StepType.CONTRACT_CREATE, 1)
            else:
                # SCORE update
                score_address = to
                context.step_counter.apply_step(StepType.CONTRACT_UPDATE, 1)

            content_size = get_deploy_content_size(context.revision, data.get('content', None))
            context.step_counter.apply_step(StepType.CONTRACT_SET, content_size)

            self._icon_score_deploy_engine.invoke(
                context=context,
                to=to,
                icon_score_address=score_address,
                data=data)
            return score_address
        elif data_type == 'deposit':
            self._deposit_handler.handle_deposit_request(context, data)
        else:
            context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
            IconScoreEngine.invoke(context, to, data_type, data)
            return None

    @staticmethod
    def _append_step_results(
            tx_result: 'TransactionResult', context: 'IconScoreContext', step_used_details: dict) -> int:
        """
        Appends step usage information to TransactionResult
        """
        final_step_used = sum(step_used_details.values())
        tx_result.step_used = final_step_used
        tx_result.cumulative_step_used = context.cumulative_step_used + final_step_used
        if final_step_used != step_used_details.get(context.msg.sender, 0):
            tx_result.step_used_details = step_used_details

        return final_step_used

    @staticmethod
    def _get_failure_from_exception(
            e: BaseException) -> TransactionResult.Failure:
        """
        Gets `Failure` from an exception
        :param e: exception
        :return: a Failure
        """

        try:
            if isinstance(e, IconServiceBaseException):
                if e.code >= ExceptionCode.SCORE_ERROR or isinstance(e, IconScoreException):
                    Logger.warning(e.message, ICON_SERVICE_LOG_TAG)
                else:
                    Logger.exception(e.message, ICON_SERVICE_LOG_TAG)

                code = int(e.code)
                message = str(e.message)
            else:
                Logger.exception(e, ICON_SERVICE_LOG_TAG)
                Logger.error(e, ICON_SERVICE_LOG_TAG)

                code: int = ExceptionCode.SYSTEM_ERROR.value
                message = str(e)
        except:
            code: int = ExceptionCode.SYSTEM_ERROR.value
            message = 'Invalid exception: code or message is invalid'

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
            TraceType.REVERT if isinstance(e, IconScoreException) else
            TraceType.THROW,
            [e.code, e.message] if isinstance(e, IconServiceBaseException) else
            [ExceptionCode.SYSTEM_ERROR, str(e)]
        )

    @staticmethod
    def _generate_logs_bloom(event_logs: List['EventLog']) -> BloomFilter:
        """
        Generates the bloom data from the event logs
        :param event_logs: The event logs
        :return: Bloom data
        """
        logs_bloom = BloomFilter()

        for event_log in event_logs:
            logs_bloom.add(EventLogEmitter.get_ordered_bytes(0xff, event_log.score_address))
            for i, indexed_item in enumerate(event_log.indexed):
                indexed_bytes = EventLogEmitter.get_ordered_bytes(i, indexed_item)
                logs_bloom.add(indexed_bytes)

        return logs_bloom

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
        return IconScoreEngine.get_score_api(
            context, icon_score_address)

    def _handle_ise_get_status(self, context: 'IconScoreContext', params: dict) -> dict:

        response = dict()
        if not bool(params) or params.get('filter'):
            last_block_status = self._make_last_block_status()
            response['lastBlock'] = last_block_status
        return response

    def _make_last_block_status(self) -> Optional[dict]:
        block = self._precommit_data_manager.last_block
        if block is None:
            block_height = -1
            block_hash = b'\x00' * 32
            timestamp = 0
            prev_block_hash = block_hash
        else:
            block_height = block.height
            block_hash = block.hash
            timestamp = block.timestamp
            prev_block_hash = block.prev_hash

        return {
            'blockHeight': block_height,
            'blockHash': block_hash,
            'timestamp': timestamp,
            'prevBlockHash': prev_block_hash
        }

    @staticmethod
    def _create_invalid_block():
        block_height = -1
        block_hash = b'\x00' * 32
        timestamp = 0
        prev_block_hash = block_hash
        return Block(block_height, block_hash, timestamp, prev_block_hash)

    def commit(self, block_height: int, instant_block_hash: bytes, block_hash: Optional[bytes]) -> None:
        """Write updated states in a context.block_batch to StateDB
        when the candidate block has been confirmed
        :param block_height: height of block being committed
        :param instant_block_hash: instant hash of block being committed
        :param block_hash: hash of block being committed
        """
        # Check for block validation before commit
        self._precommit_data_manager.validate_precommit_block(instant_block_hash)

        context = IconScoreContext(IconScoreContextType.DIRECT)

        precommit_data: 'PrecommitData' = \
            self._precommit_data_manager.get(instant_block_hash)
        block_batch = precommit_data.block_batch
        if block_hash:
            block_batch.block = Block(block_height=block_batch.block.height,
                                      block_hash=block_hash,
                                      timestamp=block_batch.block.timestamp,
                                      prev_hash=block_batch.block.prev_hash)

        new_icon_score_mapper = precommit_data.score_mapper
        if new_icon_score_mapper:
            context.icon_score_mapper.update(new_icon_score_mapper)

        self._icx_context_db.write_batch(
            context=context, states=block_batch)

        self._icx_storage.put_block_info(context, block_batch.block)
        self._precommit_data_manager.commit(block_batch.block)

        if precommit_data.precommit_flag & PrecommitFlag.STEP_ALL_CHANGED != PrecommitFlag.NONE:
            self._init_global_value_by_governance_score()

    def rollback(self, block_height: int, instant_block_hash: bytes) -> None:
        """Throw away a precommit state
        in context.block_batch and IconScoreEngine
        :param block_height: height of block which is needed to be removed from the pre-commit data manager
        :param instant_block_hash: hash of block which is needed to be removed from the pre-commit data manager
        """
        # Check for block validation before rollback
        self._precommit_data_manager.validate_precommit_block(instant_block_hash)
        self._precommit_data_manager.rollback(instant_block_hash)

    def clear_context_stack(self):
        """Clear IconScoreContext stacks
        """
        stack_size: int = self._get_context_stack_size()
        assert stack_size == 0

        if stack_size > 0:
            Logger.error(
                f'IconScoreContext leak is detected: {stack_size}',
                ICON_SERVICE_LOG_TAG)

        self._clear_context()

    def _get_last_block(self) -> Optional['Block']:
        if self._precommit_data_manager:
            return self._precommit_data_manager.last_block

        return None
