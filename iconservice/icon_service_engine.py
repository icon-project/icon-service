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
import shutil
from copy import deepcopy
from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Tuple, Dict, Union, Any

from iconcommons.logger import Logger

from iconservice.rollback import check_backup_exists
from iconservice.rollback.backup_cleaner import BackupCleaner
from iconservice.rollback.backup_manager import BackupManager
from iconservice.rollback.rollback_manager import RollbackManager
from iconservice.score_loader.icon_builtin_score_loader import IconBuiltinScoreLoader
from iconservice.score_loader.icon_score_class_loader import IconScoreClassLoader
from .base.address import Address
from .base.address import GOVERNANCE_SCORE_ADDRESS
from .base.address import SYSTEM_SCORE_ADDRESS
from .base.block import Block
from .base.exception import (
    ExceptionCode,
    IconServiceBaseException,
    IconScoreException,
    InvalidBaseTransactionException,
    InternalServiceErrorException,
    DatabaseException,
    InvalidBalanceException,
    InvalidParamsException,
)
from .base.message import Message
from .base.transaction import Transaction
from .base.type_converter_templates import ConstantKeys
from .database.db import KeyValueDatabase
from .database.factory import ContextDatabaseFactory
from .database.wal import WriteAheadLogReader, WALDBType
from .database.wal import WriteAheadLogWriter, IissWAL, StateWAL, WALState
from .deploy import DeployEngine, DeployStorage
from .fee import FeeEngine, FeeStorage, DepositHandler
from .icon_constant import (
    ICON_DEX_DB_NAME, IconServiceFlag, ConfigKey,
    Revision, BASE_TRANSACTION_INDEX,
    IISS_DB, STEP_LOG_TAG, BlockVoteStatus, WAL_LOG_TAG, ROLLBACK_LOG_TAG,
    BLOCK_INVOKE_TIMEOUT_S, RevisionChangedFlag, RPCMethod,
    DataType
)
from .iconscore.context.context import ContextContainer
from .iconscore.icon_pre_validator import IconPreValidator
from .iconscore.icon_score_context import IconScoreContext, IconScoreFuncType, IconScoreContextFactory
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_context_util import IconScoreContextUtil
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_event_log import EventLogEmitter
from .iconscore.icon_score_mapper import IconScoreMapper
from .iconscore.icon_score_result import TransactionResult
from .iconscore.icon_score_step import StepType, get_input_data_size, \
    get_deploy_content_size
from .iconscore.icon_score_trace import Trace, TraceType
from .icx import IcxEngine, IcxStorage
from .icx.issue import IssueEngine, IssueStorage
from .icx.issue.base_transaction_creator import BaseTransactionCreator
from .icx.storage import AccountPartFlag
from .icx.unstake_patcher import INVALID_EXPIRED_UNSTAKES_FILENAME
from .icx.unstake_patcher import UnstakePatcher
from .iiss import check_decentralization_condition
from .iiss.engine import Engine as IISSEngine
from .iiss.reward_calc import RewardCalcStorage
from .iiss.reward_calc.storage import IissDBNameRefactor
from .iiss.reward_calc.storage import RewardCalcDBInfo
from .iiss.storage import Storage as IISSStorage
from .inner_call import inner_call
from .inv import INVEngine, INVStorage
from .meta import MetaDBStorage
from .precommit_data_manager import PrecommitData, PrecommitDataManager, PrecommitDataWriter
from .prep import PRepEngine, PRepStorage
from .prep.data import PRep
from .rollback.metadata import Metadata as RollbackMetadata
from .utils import print_log_with_level
from .utils import sha3_256, int_to_bytes, ContextEngine, ContextStorage
from .utils import to_camel_case, bytes_to_hex
from .utils.bloom import BloomFilter
from .utils.timer import Timer

if TYPE_CHECKING:
    from .iconscore.icon_score_event_log import EventLog
    from .prep.data import Term

_TAG = "ISE"


class IconServiceEngine(ContextContainer):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconInnerService.
    """
    WAL_FILE = "block.wal"
    ROLLBACK_METADATA_FILE = "ROLLBACK_METADATA"

    def __init__(self):
        """Constructor

        """
        self._icx_context_db = None
        self._icon_pre_validator = None
        self._deposit_handler = None
        self._context_factory = None
        self._state_db_root_path: Optional[str] = None
        self._backup_root_path: Optional[str] = None
        self._rc_data_path: Optional[str] = None
        self._wal_reader: Optional['WriteAheadLogReader'] = None
        self._backup_manager: Optional[BackupManager] = None
        self._backup_cleaner: Optional[BackupCleaner] = None
        self._conf: Optional[Dict[str, Union[str, int]]] = None
        self._block_invoke_timeout_s: int = BLOCK_INVOKE_TIMEOUT_S
        self._log_dir: str = "."

        # JSON-RPC handlers
        self._handlers = {
            RPCMethod.ICX_GET_BALANCE: self._handle_icx_get_balance,
            RPCMethod.ICX_GET_TOTAL_SUPPLY: self._handle_icx_get_total_supply,
            RPCMethod.ICX_GET_SCORE_API: self._handle_icx_get_score_api,
            RPCMethod.ISE_GET_STATUS: self._handle_ise_get_status,
            RPCMethod.ICX_CALL: self._handle_icx_call,
            RPCMethod.DEBUG_ESTIMATE_STEP: self._handle_estimate_step,
            RPCMethod.ICX_SEND_TRANSACTION: self._handle_icx_send_transaction,
            RPCMethod.DEBUG_GET_ACCOUNT: self._handle_debug_get_account
        }

        self._precommit_data_manager = PrecommitDataManager()
        self._precommit_data_writer: Optional['PrecommitDataWriter'] = None

    def open(self, conf: dict):
        """Get necessary parameters and initialize diverse objects

        :param conf:
        """

        service_config_flag = self._make_service_flag(conf[ConfigKey.SERVICE])
        score_root_path: str = conf[ConfigKey.SCORE_ROOT_PATH].rstrip('/')
        score_root_path: str = os.path.abspath(score_root_path)
        state_db_root_path: str = conf[ConfigKey.STATE_DB_ROOT_PATH].rstrip('/')
        state_db_root_path: str = os.path.abspath(state_db_root_path)
        rc_data_path: str = os.path.join(state_db_root_path, IISS_DB)
        rc_socket_path: str = f"/tmp/iiss_{conf[ConfigKey.AMQP_KEY]}.sock"
        backup_root_path: str = os.path.join(state_db_root_path, "backup")
        log_dir: str = os.path.dirname(conf[ConfigKey.LOG].get(ConfigKey.LOG_FILE_PATH, "./"))

        os.makedirs(score_root_path, exist_ok=True)
        os.makedirs(state_db_root_path, exist_ok=True)
        os.makedirs(rc_data_path, exist_ok=True)
        os.makedirs(backup_root_path, exist_ok=True)

        # Share one context db with all SCORE
        ContextDatabaseFactory.open(state_db_root_path, ContextDatabaseFactory.Mode.SINGLE_DB)
        self._state_db_root_path = state_db_root_path
        self._rc_data_path = rc_data_path
        self._backup_root_path = backup_root_path

        self._icx_context_db = ContextDatabaseFactory.create_by_name(ICON_DEX_DB_NAME)
        self._context_factory = IconScoreContextFactory()

        self._deposit_handler = DepositHandler()
        self._icon_pre_validator = IconPreValidator()
        self._backup_manager = BackupManager(backup_root_path, rc_data_path)
        self._backup_cleaner = BackupCleaner(backup_root_path, conf[ConfigKey.BACKUP_FILES])

        IconScoreClassLoader.init(score_root_path)
        IconScoreContext.score_root_path = score_root_path
        IconScoreContext.icon_score_mapper = IconScoreMapper(is_threadsafe=True)
        IconScoreContext.icon_service_flag = service_config_flag
        IconScoreContext.legacy_tbears_mode = conf[ConfigKey.TBEARS_MODE]
        IconScoreContext.iiss_initial_irep = conf[ConfigKey.INITIAL_IREP]
        IconScoreContext.main_prep_count = conf[ConfigKey.PREP_MAIN_PREPS]
        IconScoreContext.main_and_sub_prep_count = conf[ConfigKey.PREP_MAIN_AND_SUB_PREPS]
        IconScoreContext.term_period = conf[ConfigKey.TERM_PERIOD]
        IconScoreContext.set_decentralize_trigger(conf[ConfigKey.DECENTRALIZE_TRIGGER])
        IconScoreContext.step_trace_flag = conf[ConfigKey.STEP_TRACE_FLAG]
        IconScoreContext.log_level = conf[ConfigKey.LOG][ConfigKey.LOG_LEVEL]
        IconScoreContext.precommitdata_log_flag = conf[ConfigKey.PRECOMMIT_DATA_LOG_FLAG]
        IconScoreContext.unstake_slot_max = conf[ConfigKey.UNSTAKE_SLOT_MAX]
        self._init_component_context()

        # Recover incomplete state on wal and rollback process
        self._recover_dbs(rc_data_path)

        # load last_block_info
        context = IconScoreContext(IconScoreContextType.DIRECT)
        self._init_last_block_info(context)

        # Remove revision from iiss_rc_db name
        IissDBNameRefactor.run(self._rc_data_path)

        # Clean up stale backup files
        self._backup_cleaner.run_on_init(context.block.height)

        self._open_component_context(context,
                                     log_dir,
                                     rc_data_path,
                                     rc_socket_path,
                                     conf[ConfigKey.IISS_META_DATA],
                                     conf[ConfigKey.IISS_CALCULATE_PERIOD],
                                     conf[ConfigKey.TERM_PERIOD],
                                     conf[ConfigKey.INITIAL_IREP],
                                     conf[ConfigKey.PREP_REGISTRATION_FEE],
                                     conf[ConfigKey.PENALTY_GRACE_PERIOD],
                                     conf[ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD],
                                     conf[ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD],
                                     conf[ConfigKey.IPC_TIMEOUT],
                                     conf[ConfigKey.ICON_RC_DIR_PATH],
                                     conf[ConfigKey.ICON_RC_MONITOR])

        self._load_builtin_scores(context,
                                  Address.from_string(conf[ConfigKey.BUILTIN_SCORE_OWNER]))

        context.engine.inv.load_inv_container(context)

        self._set_block_invoke_timeout(conf)

        # DO NOT change the values in conf
        self._conf = conf
        self._precommit_data_writer = PrecommitDataWriter(log_dir)
        self._log_dir = log_dir

    def _init_component_context(self):
        engine: 'ContextEngine' = ContextEngine(deploy=DeployEngine(),
                                                fee=FeeEngine(),
                                                icx=IcxEngine(),
                                                iiss=IISSEngine(),
                                                prep=PRepEngine(),
                                                issue=IssueEngine(),
                                                inv=INVEngine())

        storage: 'ContextStorage' = ContextStorage(deploy=DeployStorage(self._icx_context_db),
                                                   fee=FeeStorage(self._icx_context_db),
                                                   icx=IcxStorage(self._icx_context_db),
                                                   iiss=IISSStorage(self._icx_context_db),
                                                   prep=PRepStorage(self._icx_context_db),
                                                   issue=IssueStorage(self._icx_context_db),
                                                   meta=MetaDBStorage(self._icx_context_db),
                                                   rc=RewardCalcStorage(),
                                                   inv=INVStorage(self._icx_context_db))

        IconScoreContext.engine = engine
        IconScoreContext.storage = storage

    def _init_last_block_info(self, context: 'IconScoreContext'):
        context.storage.icx.load_last_block_info(context)
        self._precommit_data_manager.init(IconScoreContext.storage.icx.last_block)
        context.block = self._get_last_block()

    @classmethod
    def _open_component_context(cls,
                                context: 'IconScoreContext',
                                log_dir: str,
                                rc_data_path: str,
                                rc_socket_path: str,
                                iiss_meta_data: dict,
                                calc_period: int,
                                term_period: int,
                                irep: int,
                                prep_reg_fee: int,
                                penalty_grace_period: int,
                                low_productivity_penalty_threshold: int,
                                block_validation_penalty_threshold: int,
                                ipc_timeout: int,
                                icon_rc_path: str,
                                icon_rc_monitor: bool):
        # storages MUST be prepared prior to engines because engines use them on open()
        IconScoreContext.storage.deploy.open(context)
        IconScoreContext.storage.fee.open(context)
        IconScoreContext.storage.icx.open(context)
        IconScoreContext.storage.iiss.open(context, iiss_meta_data, calc_period)
        IconScoreContext.storage.prep.open(context, prep_reg_fee)
        IconScoreContext.storage.issue.open(context)
        IconScoreContext.storage.meta.open(context)
        IconScoreContext.storage.rc.open(context, rc_data_path)
        IconScoreContext.storage.inv.open(context)

        IconScoreContext.engine.deploy.open(context)
        IconScoreContext.engine.fee.open(context)
        IconScoreContext.engine.icx.open(context)
        IconScoreContext.engine.iiss.open(context,
                                          log_dir,
                                          rc_data_path,
                                          rc_socket_path,
                                          ipc_timeout,
                                          icon_rc_path,
                                          icon_rc_monitor)
        IconScoreContext.engine.prep.open(context,
                                          term_period,
                                          irep,
                                          penalty_grace_period,
                                          low_productivity_penalty_threshold,
                                          block_validation_penalty_threshold)
        IconScoreContext.engine.issue.open(context)
        IconScoreContext.engine.inv.open(context)

    @classmethod
    def _close_component_context(cls, context: 'IconScoreContext'):
        IconScoreContext.engine.deploy.close()
        IconScoreContext.engine.fee.close()
        IconScoreContext.engine.icx.close()
        IconScoreContext.engine.iiss.close()
        IconScoreContext.engine.prep.close()
        IconScoreContext.engine.issue.close()
        IconScoreContext.engine.inv.close()

        IconScoreContext.storage.deploy.close(context)
        IconScoreContext.storage.fee.close(context)
        IconScoreContext.storage.icx.close(context)
        IconScoreContext.storage.iiss.close(context)
        IconScoreContext.storage.prep.close(context)
        IconScoreContext.storage.issue.close(context)
        IconScoreContext.storage.meta.close(context)
        IconScoreContext.storage.rc.close()
        IconScoreContext.storage.inv.close(context)

    @classmethod
    def get_ready_future(cls):
        return IconScoreContext.engine.iiss.get_ready_future()

    @classmethod
    def is_reward_calculator_ready(cls) -> bool:
        return IconScoreContext.engine.iiss.is_reward_calculator_ready()

    @staticmethod
    def _make_service_flag(flag_table: dict) -> int:
        make_flag = 0
        for flag in IconServiceFlag:
            flag_name = to_camel_case(flag.name.lower())
            is_enable = flag_table.get(flag_name, False)
            if is_enable:
                make_flag |= flag
        return make_flag

    def _load_builtin_scores(self, context: 'IconScoreContext', builtin_score_owner: 'Address'):
        context.icon_score_mapper.clear()

        current_address: 'Address' = context.current_address
        context.current_address = GOVERNANCE_SCORE_ADDRESS

        try:
            self._push_context(context)
            IconBuiltinScoreLoader.load_builtin_scores(context, builtin_score_owner)
        finally:
            self._pop_context()

        context.current_address = current_address

    def close(self) -> None:
        """Free all resources occupied by IconServiceEngine
        including db, memory and so on
        """
        context = IconScoreContext(IconScoreContextType.DIRECT)
        context.block = self._precommit_data_manager.last_block
        try:
            self._push_context(context)

            IconScoreContext.icon_score_mapper.close()
            IconScoreContext.icon_score_mapper = None

            self._close_component_context(context)

            IconScoreClassLoader.close(context.score_root_path)
        finally:
            self._pop_context()
            ContextDatabaseFactory.close()
            self._clear_context()

    def invoke(self,
               block: 'Block',
               tx_requests: list,
               prev_block_generator: Optional['Address'] = None,
               prev_block_validators: Optional[List['Address']] = None,
               prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
               is_block_editable: bool = False) -> Tuple[List['TransactionResult'], bytes, dict, Optional[dict]]:

        """Process transactions in a block sent by loopchain

        :param block:
        :param tx_requests: transactions in a block
        :param prev_block_generator: previous block generator
        :param prev_block_validators: previous block validators (legacy)
        :param prev_block_votes: previous block vote info
        :param is_block_editable: boolean which imply whether creating base transaction or not
        :return: (TransactionResult[], bytes, added transaction{}, main prep as dict{})
        """
        # If the block has already been processed,
        # return the result from PrecommitDataManager
        precommit_data: 'PrecommitData' = self._precommit_data_manager.get(block.hash)
        if precommit_data is not None:
            if not precommit_data.already_exists:
                Logger.info(tag=_TAG,
                            msg=f"Block result already exists: \n{precommit_data}")
                self._precommit_data_writer.write(precommit_data)
                precommit_data.already_exists = True
            else:
                Logger.info(tag=_TAG,
                            msg=f"Block result already exists: \n"
                                f"state_root_hash={bytes_to_hex(precommit_data.state_root_hash)}")

            return \
                precommit_data.block_result, \
                precommit_data.state_root_hash, \
                precommit_data.added_transactions, \
                precommit_data.next_preps

        # Check for block validation before invoke
        self._precommit_data_manager.validate_block_to_invoke(block)

        context: 'IconScoreContext' = self._context_factory.create(
            IconScoreContextType.INVOKE,
            block=block,
            prev_block_batches=self._precommit_data_manager.get_block_batches(block.prev_hash))

        # TODO: prev_block_votes must be support to low version about prev_block_validators by using meta storage.
        prev_block_votes: Optional[List[Tuple['Address', int]]] = \
            self._get_prev_block_votes(context,
                                       prev_block_generator,
                                       prev_block_validators,
                                       prev_block_votes)
        prev_block_generator = \
            context.prep_address_converter.get_prep_address_from_node_address(prev_block_generator)

        # For RC DB
        rc_db_revision: int = self._get_rc_db_revision_before_process_transactions(context)

        block_result = []
        added_transactions = {}

        self._before_transaction_process(context,
                                         is_block_editable,
                                         tx_requests,
                                         added_transactions,
                                         prev_block_generator,
                                         prev_block_votes)

        if block.height == 0:
            # Assume that there is only one tx in genesis_block
            tx_result = self._invoke_genesis(context, tx_requests[0], 0)
            block_result.append(tx_result)
            context.block_batch.update(context.tx_batch)
            context.tx_batch.clear()
        else:
            tx_timer = Timer()
            tx_timer.start()

            for index, tx_request in enumerate(tx_requests):
                tx_hash: Optional[bytes] = tx_request["params"].get("txHash")
                Logger.debug(_TAG, f"INVOKE tx: tx_hash={bytes_to_hex(tx_hash)} {tx_request}")

                # Adjust the number of transactions in a block to make sure that
                # a leader can broadcast a block candidate to validators in a specific period.
                if is_block_editable and not self._continue_to_invoke(tx_request, tx_timer):
                    Logger.info(
                        tag=_TAG,
                        msg=f"Stop to invoke remaining transactions: {index} / {len(tx_requests)}")
                    break

                if index == BASE_TRANSACTION_INDEX and context.is_decentralized():
                    if not tx_request['params'].get('dataType') == "base":
                        raise InvalidBaseTransactionException(
                            "Invalid block: first transaction must be an base transaction")
                    tx_result = self._invoke_base_request(context, tx_request, is_block_editable)
                else:
                    tx_result = self._invoke_request(context, tx_request, index)

                self._log_step_trace(context)
                block_result.append(tx_result)
                context.update_batch()

                # for migration governance SCORE
                context.engine.inv.update_inv_container_by_result(context, tx_result)

                if context.is_revision_changed(Revision.IISS.value):
                    context.revision_changed_flag |= RevisionChangedFlag.GENESIS_IISS_CALC

                if context.revision >= Revision.IISS.value:
                    context.block_batch.block.cumulative_fee += tx_result.step_price * tx_result.step_used

                if context.is_revision_changed(Revision.FIX_BALANCE_BUG.value):
                    self._run_unstake_patcher(context)

                Logger.debug(_TAG, f"INVOKE txResult: {tx_result}")

        if self._check_end_block_height_of_calc(context):
            context.revision_changed_flag |= RevisionChangedFlag.IISS_CALC
            if check_decentralization_condition(context):
                context.revision_changed_flag |= RevisionChangedFlag.DECENTRALIZATION
                Logger.info(tag=_TAG,
                            msg=f"Decentralization condition is met: {context.block}")

                # When decentralization begins,
                # change the reward calculation period from 43200 to 43120 which is the same as term_period
                context.storage.iiss.put_calc_period(context, context.term_period)

        next_preps, term, rc_state_hash = self._after_transaction_process(context,
                                                                          rc_db_revision,
                                                                          prev_block_generator,
                                                                          prev_block_votes)

        # Save precommit data
        # It will be written to levelDB on commit
        precommit_data = PrecommitData(context.revision,
                                       rc_db_revision,
                                       context.inv_container,
                                       context.block_batch,
                                       block_result,
                                       context.rc_block_batch,
                                       context.preps,
                                       term,
                                       prev_block_generator,
                                       prev_block_validators,
                                       context.new_icon_score_mapper,
                                       rc_state_hash,
                                       added_transactions,
                                       next_preps,
                                       context.prep_address_converter)
        if context.precommitdata_log_flag:
            Logger.info(tag=_TAG,
                        msg=f"Created precommit_data: \n{precommit_data}")
        self._precommit_data_manager.push(precommit_data)
        return \
            block_result, \
            precommit_data.state_root_hash, \
            precommit_data.added_transactions, \
            precommit_data.next_preps

    @classmethod
    def _get_rc_db_revision_before_process_transactions(cls, context: 'IconScoreContext') -> int:

        if context.revision < Revision.IISS.value:
            return 0

        start: int = context.engine.iiss.get_start_block_of_calc(context)
        if start == context.block.height:
            return context.revision
        else:
            return cls._get_revision_from_rc(context)

    @classmethod
    def _get_revision_from_rc(cls,
                              context: 'IconScoreContext') -> int:
        version, revision = context.storage.rc.get_version_and_revision()
        return revision

    @classmethod
    def _get_prev_block_votes(cls,
                              context: 'IconScoreContext',
                              prev_block_generator: Optional['Address'] = None,
                              prev_block_validators: Optional[List['Address']] = None,
                              prev_block_votes: Optional[List[Tuple['Address', int]]] = None) -> \
            Optional[List[Tuple['Address', int]]]:

        """
        If prev_block_votes is valid field, you can just return origin data but if not,
        you have to make prev_block_votes by using meta storage and prev_block_validators params for being simple logic.

        :param context:
        :param prev_block_validators:
        :param prev_block_votes:
        :return:
        """
        if prev_block_generator:
            if prev_block_votes:
                return cls._convert_node_address_to_prep_address(context, prev_block_votes)
            elif prev_block_validators:
                return cls._convert_validators_to_votes(context, prev_block_generator, prev_block_validators)

        return None

    @classmethod
    def _convert_node_address_to_prep_address(cls,
                                              context: 'IconScoreContext',
                                              prev_block_votes: Optional[List[Tuple['Address', int]]]) -> \
            Optional[List[Tuple['Address', int]]]:
        """Convert node_address in prev_block_votes to prep_address

        """

        new_prev_block_votes: List[Tuple['Address', int]] = []

        for node_address, vote in prev_block_votes:
            # prep_address can be the same as node_address
            # if P-Rep does not have its specific node_address
            prep_address: 'Address' = \
                context.prep_address_converter.get_prep_address_from_node_address(node_address)
            new_prev_block_votes.append([prep_address, vote])

        return new_prev_block_votes

    @classmethod
    def _convert_validators_to_votes(cls,
                                     context: 'IconScoreContext',
                                     prev_block_generator: 'Address',
                                     prev_block_validators: Optional[List['Address']]) -> list:

        prev_block_votes: List[Tuple['Address', int]] = []
        last_main_preps: List['Address'] = context.storage.meta.get_last_main_preps(context)

        for address in last_main_preps:
            if address == prev_block_generator:
                continue
            else:
                # we can't support denied vote in low version.
                # so we can set only Approve.
                vote_status: 'BlockVoteStatus' = BlockVoteStatus.NONE
                if address in prev_block_validators:
                    vote_status: 'BlockVoteStatus' = BlockVoteStatus.TRUE

                prev_block_votes.append([address, vote_status.value])

        return prev_block_votes

    @classmethod
    def _log_step_trace(cls, context: 'IconScoreContext'):
        """If steptrace option is turned on, write step trace messages to a log file

        :param context:
        :return:
        """
        try:
            if context.step_counter.step_tracer is not None:
                msg: str = f"txHash(0x{context.tx.hash.hex()})\n{context.step_counter.step_tracer}"
                print_log_with_level(context.log_level, tag=STEP_LOG_TAG, msg=msg)
        except:
            pass

    def _before_transaction_process(self,
                                    context: 'IconScoreContext',
                                    is_block_editable: bool,
                                    tx_requests: list,
                                    added_transactions: dict,
                                    prev_block_generator: Optional['Address'],
                                    prev_block_votes: Optional[List[Tuple['Address', int]]]):

        # if you want to use rc_version here, you must use it.
        # rc_db_revision: int = self._get_revision_from_rc(context)

        self._check_calculate_done(context)

        if not context.is_decentralized():
            return

        self._make_base_transaction(context, is_block_editable, tx_requests, added_transactions)

        # Skip the first block after decentralization
        if context.is_the_first_block_on_decentralization():
            Logger.info(tag=_TAG,
                        msg=f"The first block of decentralization: {context.block}")
            return

        self._update_productivity(context, prev_block_generator, prev_block_votes)
        self._update_last_generate_block_height(context, prev_block_generator)

        context.prep_address_converter.reset_prev_node_address()

    @classmethod
    def _check_calculate_done(cls,
                              context: 'IconScoreContext'):

        end_block: int = context.storage.iiss.get_end_block_height_of_calc(context)
        if end_block == context.block.height:
            iscore, rc_latest_calculate_bh, _ = context.storage.rc.get_calc_response_from_rc()
            period: int = context.storage.iiss.get_calc_period(context)

            latest_calculate_bh: int = end_block - period

            # Check if the response has been received
            if iscore == -1:
                iscore, calc_bh, state_hash = context.engine.iiss.query_calculate_result(latest_calculate_bh)
                context.storage.rc.put_calc_response_from_rc(iscore, calc_bh, state_hash)
            else:
                context.engine.iiss.check_calculate_request_block_height(rc_latest_calculate_bh,
                                                                         latest_calculate_bh)

    @classmethod
    def _make_base_transaction(cls,
                               context: 'IconScoreContext',
                               is_block_editable: bool,
                               tx_requests: list,
                               added_transactions: dict):

        if is_block_editable:
            base_transaction: dict = BaseTransactionCreator.create_base_transaction(context)
            # todo: if the txHash field is add to addedTransaction, should remove this logic
            tx_params_to_added = deepcopy(base_transaction["params"])
            del tx_params_to_added["txHash"]
            tx_hash: bytes = base_transaction["params"]["txHash"]
            added_transactions[tx_hash.hex()] = tx_params_to_added
            tx_requests.insert(0, base_transaction)

    @classmethod
    def _after_transaction_process(
            cls,
            context: 'IconScoreContext',
            rc_db_revision: int,
            prev_block_generator: Optional['Address'] = None,
            prev_block_votes: Optional[List[Tuple['Address', int]]] = None) \
            -> Tuple[Optional[dict], Optional['Term'], bytes]:
        """If the current term is ended, prepare the next term,
        - Prepare the list of main P-Reps for the next term which is passed to loopchain
        - Calculate the weighted average of ireps
        submitted by P-Rep candidates that will run as main P-Reps during the next term
        - Impose low productivity penalty on the current main P-Reps which did not validate more than 15% of blocks

        :param context:
        :param rc_db_revision
        :param prev_block_generator:
        :param prev_block_votes:
        :return: (next_preps, term, rc_state_hash)
        """

        next_preps, term = context.engine.prep.on_block_invoked(
            context, bool(context.revision_changed_flag & RevisionChangedFlag.DECENTRALIZATION))

        rc_state_hash: Optional[bytes] = None
        if context.revision >= Revision.IISS.value:
            rc_state_hash: Optional[bytes] = context.engine.iiss.update_db(context,
                                                                           term,
                                                                           prev_block_generator,
                                                                           prev_block_votes,
                                                                           rc_db_revision)
        context.storage.meta.put_prep_address_converter(context, context.prep_address_converter)
        context.update_batch()

        if next_preps is not None:
            Logger.info(tag="TERM", msg=f"{next_preps}")

        return next_preps, term, rc_state_hash

    @classmethod
    def _update_productivity(cls,
                             context: 'IconScoreContext',
                             prev_block_generator: Optional['Address'],
                             prev_block_votes: Optional[List[Tuple['Address', int]]]):

        """Update block validation statistics of Main P-Reps
        This method should be called only after decentralization

        :param context:
        :param prev_block_generator:
        :param prev_block_votes:
        :return:
        """

        if prev_block_generator is None or prev_block_votes is None:
            Logger.warning(tag=_TAG, msg=f"No block validators: block={context.block}")
            return

        validators: List[Tuple['Address', int]] = [[prev_block_generator, BlockVoteStatus.TRUE.value]]
        validators.extend(prev_block_votes)

        Logger.info(f"update_productivity(validators): {validators}")

        for address, vote_state in validators:
            dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
            assert isinstance(dirty_prep, PRep), f"dirty_prep: {address}"

            is_validator: bool = vote_state != BlockVoteStatus.NONE.value

            dirty_prep.update_block_statistics(is_validator)
            context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

    @classmethod
    def _update_last_generate_block_height(cls,
                                           context: 'IconScoreContext',
                                           prev_block_generator: Optional['Address']):
        """This method should be called only after decentralization

        :param context:
        :param prev_block_generator:
        :return:
        """
        if prev_block_generator is None:
            return

        dirty_prep: 'PRep' = context.get_prep(prev_block_generator, mutable=True)
        assert isinstance(dirty_prep, PRep), f"dirty_prep: {dirty_prep.address}"

        dirty_prep.last_generate_block_height = context.block.height - 1
        context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

    @staticmethod
    def _check_end_block_height_of_calc(context: 'IconScoreContext') -> bool:
        if context.revision < Revision.IISS.value:
            return False

        check_end_block_height: Optional[int] = context.storage.iiss.get_end_block_height_of_calc(context)
        if check_end_block_height is None:
            return False

        return context.block.height == check_end_block_height

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

            context.storage.icx.put_genesis_accounts(context, accounts)

            tx_result.status = TransactionResult.SUCCESS

        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)

        return tx_result

    def _process_base_transaction(self,
                                  context: 'IconScoreContext',
                                  issue_data: dict):

        treasury_address: 'Address' = context.storage.icx.fee_treasury
        tx_result = TransactionResult(context.tx, context.block)
        tx_result.to = treasury_address

        # proceed issue
        context.engine.issue.issue(context,
                                   treasury_address,
                                   issue_data)

        if context.engine.prep.term.start_block_height == context.block.height:
            EventLogEmitter.emit_event_log(context,
                                           score_address=SYSTEM_SCORE_ADDRESS,
                                           event_signature='TermStarted(int,int,int)',
                                           arguments=[context.engine.prep.term.sequence,
                                                      context.engine.prep.term.start_block_height,
                                                      context.engine.prep.term.end_block_height],
                                           indexed_args_count=0)

        # Handles to impose low productivity and block validation penalties, if exists
        context.engine.prep.impose_penalty(context)

        tx_result.status = TransactionResult.SUCCESS
        tx_result.event_logs = context.event_logs
        if context.revision >= Revision.ADD_LOGS_BLOOM_ON_BASE_TX.value:
            tx_result.logs_bloom = self._generate_logs_bloom(context.event_logs)
        tx_result.traces = context.traces

        return tx_result

    def _invoke_base_request(self,
                             context: 'IconScoreContext',
                             request: dict,
                             is_block_editable: bool) -> 'TransactionResult':
        assert 'params' in request
        assert 'data' in request['params']

        issue_data_in_tx: dict = request['params'].get('data')
        if not is_block_editable:
            issue_data_in_db: dict = context.engine.issue.create_icx_issue_info(context)
            if issue_data_in_tx != issue_data_in_db:
                raise InvalidBaseTransactionException("Have difference between "
                                                      "base transaction and actual db data. "
                                                      f"base tx: {issue_data_in_tx} "
                                                      f"db: {issue_data_in_db} ")

        context.tx = Transaction(tx_hash=request['params']['txHash'],
                                 index=BASE_TRANSACTION_INDEX,
                                 origin=None,
                                 timestamp=context.block.timestamp,
                                 nonce=None)

        context.event_logs = []
        context.traces = []
        context.msg_stack.clear()
        context.event_log_stack.clear()

        tx_result = self._process_base_transaction(context, issue_data_in_tx)
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
        step_limit: int = params.get('stepLimit')

        context.tx = Transaction(tx_hash=params['txHash'],
                                 index=index,
                                 origin=from_,
                                 to=to,
                                 timestamp=params.get('timestamp', context.block.timestamp),
                                 nonce=params.get('nonce', None))

        context.msg = Message(sender=from_, value=params.get('value', 0))
        context.current_address = to
        context.event_logs = []
        context.traces = []
        context.set_step_counter(step_limit=step_limit)
        context.msg_stack.clear()
        context.event_log_stack.clear()
        context.fee_sharing_proportion = 0

        return self._call(context, method, params)

    @classmethod
    def _estimate_step_by_request(cls, request, context) -> int:
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
            if to == SYSTEM_SCORE_ADDRESS:
                context.step_counter.apply_step(StepType.CONTRACT_CREATE, 1)
            # When updating SCORE.
            else:
                context.step_counter.apply_step(StepType.CONTRACT_UPDATE, 1)

        return context.step_counter.step_used

    def _estimate_step_by_execution(self, request, context) -> int:
        """Processes the transaction and estimates step.

        :param request:
        :param context:
        """
        method: str = request['method']
        params: dict = request['params']

        from_: Address = params['from']
        to: Address = params['to']

        last_block: 'Block' = self._get_last_block()
        timestamp = params.get('timestamp', last_block.timestamp)
        context.tx = Transaction(tx_hash=sha3_256(int_to_bytes(timestamp)),
                                 index=0,
                                 origin=from_,
                                 timestamp=timestamp,
                                 nonce=params.get('nonce', None))
        context.msg = Message(sender=from_, value=params.get('value', 0))
        context.current_address = to
        context.event_logs = []
        context.traces = []

        # Deposits virtual ICXs to the sender to prevent validation error due to 'out of balance'.
        account = context.storage.icx.get_account(context, from_)
        account.deposit(context.step_counter.step_limit * context.step_counter.step_price + params.get('value', 0))
        context.storage.icx.put_account(context, account)
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
        context = self._context_factory.create(IconScoreContextType.ESTIMATION, block=self._get_last_block())
        context.set_step_counter()

        params: dict = request['params']
        data_type: str = params.get('dataType')
        to: Address = params['to']

        if data_type == "deploy" or not to.is_contract:
            # Calculates simply and estimates step with request data.
            return self._estimate_step_by_request(request, context)
        else:
            # Processes the transaction and estimates step.
            return self._estimate_step_by_execution(request, context)

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
        context: 'IconScoreContext' = self._context_factory.create(
            IconScoreContextType.QUERY,
            block=self._get_last_block()
        )

        if params:
            from_: 'Address' = params.get('from', None)
            context.msg = Message(sender=from_)
            step_limit: Optional[int] = params.get('stepLimit')
        else:
            step_limit = None

        context.traces = []
        context.set_step_counter(step_limit=step_limit)

        ret = self._call(context, method, params)
        return ret

    def validate_transaction(self, request: dict, origin_request: dict) -> None:
        """Validate JSON-RPC transaction request
        before putting it into transaction pool

        JSON Schema validator checks basic JSON-RPC request syntax
        on JSON-RPC Server
        IconPreValidator focuses on business logic and semantic problems

        :param origin_request: JSON_RPC Original request for more strict validate
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

        context = self._context_factory.create(IconScoreContextType.QUERY, self._get_last_block())
        context.set_step_counter()

        origin_params = origin_request['params']

        try:
            self._push_context(context)

            step_price: int = context.step_counter.step_price
            minimum_step: int = context.inv_container.step_costs.get(StepType.DEFAULT, 0)

            if 'data' in params:
                # minimum_step is the sum of
                # default STEP cost and input STEP costs if data field exists
                data = params['data']
                input_size = get_input_data_size(context.revision, data)
                minimum_step += input_size * context.inv_container.step_costs.get(StepType.INPUT, 0)
            self._icon_pre_validator.origin_request_execute(origin_params, context.revision)
            self._icon_pre_validator.execute(context, params, step_price, minimum_step)

            if to.is_contract:
                # SCORE updating is not blocked by SCORE blacklist
                IconScoreContextUtil.validate_score_blacklist(context, to)

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

    @classmethod
    def _handle_icx_get_balance(cls,
                                context: 'IconScoreContext',
                                params: dict) -> int:
        """Returns the icx balance of the given address

        :param context:
        :param params:
        :return: icx balance in loop
        """
        address = params['address']
        return context.engine.icx.get_balance(context, address)

    @classmethod
    def _handle_icx_get_total_supply(cls,
                                     context: 'IconScoreContext',
                                     _params: dict) -> int:
        """Returns the amount of icx total supply

        :param context:
        :param _params:
        :return: icx amount in loop (1 icx == 1e18 loop)
        """
        return context.storage.icx.get_total_supply(context)

    @classmethod
    def _handle_icx_call(cls,
                         context: 'IconScoreContext',
                         params: dict) -> object:
        """Handles an icx_call json-rpc request

        State change is possible in icx_call message

        :param params:
        :return:
        """

        to: Address = params['to']
        data_type = params.get('dataType', None)
        data = params.get('data', None)

        context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
        if to.is_contract:
            return IconScoreEngine.query(context, to, data_type, data)

        raise InvalidParamsException(
            f"Mismatch between to and dataType: to={to} dataType={data_type}"
        )

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
            self._process_transaction(context, params, tx_result)
            tx_result.status = TransactionResult.SUCCESS
        except InvalidBalanceException as e:
            # If InvalidBalanceException is raised, stop to invoke this block
            # Because balance integrity is broken
            Logger.exception(tag=_TAG, msg=str(e))
            raise e
        except BaseException as e:
            tx_result.failure = self._get_failure_from_exception(e)
            trace = self._get_trace_from_exception(context.current_address, e)
            context.clear_batch()
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
        tx_result: 'TransactionResult' = TransactionResult(context.tx, context.block)
        self._process_transaction(context, params, tx_result)

        return context.step_counter.max_step_used

    def _process_transaction(self,
                             context: 'IconScoreContext',
                             params: dict,
                             tx_result: 'TransactionResult') -> None:
        """
        Processes the transaction

        :param params: JSON-RPC params
        """
        # Checks the balance only on the invoke context(skip estimate context)
        if context.type == IconScoreContextType.INVOKE:
            tmp_context: 'IconScoreContext' = IconScoreContext(IconScoreContextType.QUERY)
            tmp_context.block = self._get_last_block()
            # Check if from account can charge a tx fee
            self._icon_pre_validator.execute_to_check_out_of_balance(
                context if context.revision >= Revision.THREE.value else tmp_context,
                params,
                step_price=context.step_counter.step_price)

        # Every send_transaction are calculated DEFAULT STEP at first
        context.step_counter.apply_step(StepType.DEFAULT, 1)
        input_size = get_input_data_size(context.revision, params.get('data', None))
        context.step_counter.apply_step(StepType.INPUT, input_size)

        to: Address = params['to']
        data_type: Optional[str] = params.get('dataType')

        self._validate_data_type(context, to, data_type)

        # Can't transfer ICX to system SCORE
        if data_type in (None, DataType.CALL, DataType.MESSAGE):
            self._transfer_coin(context, params)

        if to.is_contract:
            tx_result.score_address = self._handle_score_invoke(context, to, params)

    def _validate_data_type(
            self, context: 'IconScoreContext', to: 'Address', data_type: Optional[str]
    ):
        try:
            self._icon_pre_validator.validate_data_type(context, to, data_type)
        except InvalidParamsException as e:
            if data_type == DataType.CALL:
                context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
            elif data_type == DataType.DEPLOY:
                context.step_counter.apply_step(StepType.CONTRACT_UPDATE, 1)

            raise e

    @classmethod
    def _transfer_coin(cls,
                       context: 'IconScoreContext',
                       params: dict) -> None:
        """Transfer ICX coin from EOA to account.
        JSON-RPC syntax validation has already been complete

        :param context:
        :param params:
        :return:
        """
        from_: 'Address' = params['from']
        to: 'Address' = params['to']
        value: int = params.get('value', 0)

        if (
                to == SYSTEM_SCORE_ADDRESS
                and context.revision < Revision.BURN_V2_ENABLED.value
        ):
            # Prevent system score from receiving ICX
            # if context.revision is less than Revision.BURN_V2_ENABLED(12)
            return

        context.engine.icx.transfer(context, from_, to, value)

    @classmethod
    def _charge_transaction_fee(cls,
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
            step_used_details = context.engine.fee.charge_transaction_fee(
                context, from_, to, step_price, step_used, context.block.height)
        except BaseException as e:
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = str(e)
            Logger.exception(message, _TAG)
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

        if data_type == DataType.DEPLOY:
            return context.engine.deploy.invoke(context, to, data)
        elif data_type == DataType.DEPOSIT:
            self._deposit_handler.handle_deposit_request(context, data)
            return None
        else:
            if self._check_contract_call_step(context, to, data_type):
                context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
            IconScoreEngine.invoke(context, to, data_type, data)
            return None

    @staticmethod
    def _check_contract_call_step(context: 'IconScoreContext',
                                  to: 'Address',
                                  data_type: Optional[str]) -> bool:
        # do not charge CONTRACT_CALL step when call system SCORE
        # exceptions for mainnet backward compatibility:
        #   - dataType is not 'call'
        if to == SYSTEM_SCORE_ADDRESS:
            return (
                context.revision < Revision.SYSTEM_SCORE_ENABLED.value
                and data_type != DataType.CALL
            )

        return True

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
                    Logger.warning(e.message, _TAG)
                else:
                    Logger.exception(e.message, _TAG)

                code = int(e.code)
                message = str(e.message)
            else:
                Logger.exception(str(e), _TAG)
                Logger.error(str(e), _TAG)

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

    @classmethod
    def _handle_icx_get_score_api(cls,
                                  context: 'IconScoreContext',
                                  params: dict) -> object:
        """Handles an icx_get_score_api JSON-RPC request

        get score api

        :param context:
        :param params:
        :return:
        """
        icon_score_address: Address = params['address']
        return IconScoreEngine.get_score_api(
            context, icon_score_address)

    def _handle_ise_get_status(self, _context: 'IconScoreContext', params: dict) -> dict:

        response = dict()
        if not bool(params) or params.get('filter'):
            last_block_status = self._make_last_block_status()
            response['lastBlock'] = last_block_status
        return response

    def _make_last_block_status(self) -> Optional[dict]:
        block = self._get_last_block()
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

    def commit(self, block_height: int, instant_block_hash: bytes, block_hash: bytes) -> None:
        """Write updated states in a context.block_batch to StateDB
        when the precommit block has been confirmed
        :param block_height: height of block being committed
        :param instant_block_hash: instant hash of block being committed
        :param block_hash: hash of block being committed
        """
        if instant_block_hash != block_hash:
            # Only a leader node replaces the instant_block_hash with an official block_hash
            self._precommit_data_manager.change_block_hash(
                block_height, instant_block_hash, block_hash)

        # Check for block validation before commit
        self._precommit_data_manager.validate_block_to_commit(block_hash)

        precommit_data: 'PrecommitData' = self._precommit_data_manager.get(block_hash)
        # Add last_block info to block_batch in order to record the data to stateDB
        precommit_data.block_batch.set_block_to_batch(precommit_data.revision)

        context = self._context_factory.create(IconScoreContextType.DIRECT, block=precommit_data.block)

        if precommit_data.revision < Revision.IISS.value:
            self._commit_before_iiss(context, precommit_data)
        else:
            self._commit_after_iiss(context, precommit_data, instant_block_hash)

    def _commit_before_iiss(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        state_wal: 'StateWAL' = StateWAL(precommit_data.block_batch)
        self._process_state_commit(context, precommit_data, state_wal)

    def _commit_after_iiss(self,
                           context: 'IconScoreContext',
                           precommit_data: 'PrecommitData',
                           instant_block_hash: bytes):
        # Check if this block is the start block of a calculation period
        start_calc_block_height: int = context.engine.iiss.get_start_block_of_calc(context)
        is_calc_period_start_block: bool = context.block.height == start_calc_block_height

        wal_writer, state_wal, iiss_wal = \
            self._process_wal(context, precommit_data, is_calc_period_start_block, instant_block_hash)
        wal_writer.flush()

        # Backup the previous block state
        self._backup_manager.run(
            icx_db=self._icx_context_db.key_value_db,
            rc_db=context.storage.rc.key_value_db,
            revision=context.revision,
            prev_block=self._get_last_block(),
            block_batch=precommit_data.block_batch,
            iiss_wal=iiss_wal,
            is_calc_period_start_block=is_calc_period_start_block,
            instant_block_hash=instant_block_hash)

        # Clean up the oldest backup file
        self._backup_cleaner.run_on_commit(context.block.height)

        # Write iiss_wal to rc_db
        standby_db_info: Optional['RewardCalcDBInfo'] = \
            self._process_iiss_commit(context, precommit_data, iiss_wal, is_calc_period_start_block)
        wal_writer.write_state(WALState.WRITE_RC_DB.value, add=True)
        wal_writer.flush()

        # Write state_wal to state_db
        self._process_state_commit(context, precommit_data, state_wal)
        wal_writer.write_state(WALState.WRITE_STATE_DB.value, add=True)
        wal_writer.flush()

        # send IPC
        self._process_ipc(context, wal_writer, precommit_data, standby_db_info, instant_block_hash)
        wal_writer.close()

        try:
            os.remove(self._get_write_ahead_log_path())
        except BaseException as e:
            Logger.error(tag=_TAG, msg=str(e))

    def _process_wal(self, context: 'IconScoreContext',
                     precommit_data: 'PrecommitData',
                     is_calc_period_start_block: bool,
                     instant_block_hash: bytes) \
            -> Tuple['WriteAheadLogWriter', 'StateWAL', Optional['IissWAL']]:
        """Assume that this method is called after Revision.IISS is on

        :param context:
        :param precommit_data:
        :param is_calc_period_start_block:
        :return:
        """
        assert precommit_data.revision >= Revision.IISS.value

        block: 'Block' = precommit_data.block
        wal_path: str = self._get_write_ahead_log_path()
        state_wal: 'StateWAL' = StateWAL(precommit_data.block_batch)

        # At the start of calc period, put revision and version to newly created current_rc_db
        revision: int = precommit_data.rc_db_revision if is_calc_period_start_block else -1

        tx_index: int = context.storage.rc.get_tx_index(is_calc_period_start_block)
        Logger.info(tag=_TAG, msg=f"tx_index={tx_index}")
        iiss_wal: 'IissWAL' = IissWAL(precommit_data.rc_block_batch, tx_index, revision)

        wal_writer: 'WriteAheadLogWriter' = \
            WriteAheadLogWriter(precommit_data.revision,
                                max_log_count=2,
                                block=block,
                                instant_block_hash=instant_block_hash)
        wal_writer.open(wal_path)

        if is_calc_period_start_block:
            wal_writer.write_state(WALState.CALC_PERIOD_START_BLOCK.value, add=False)

        wal_writer.write_walogable(iiss_wal)
        wal_writer.write_walogable(state_wal)

        return wal_writer, state_wal, iiss_wal

    def _process_state_commit(self,
                              context: 'IconScoreContext',
                              precommit_data: 'PrecommitData',
                              state_wal: 'StateWAL'):
        new_icon_score_mapper = precommit_data.score_mapper
        if new_icon_score_mapper:
            IconScoreContext.icon_score_mapper.update(new_icon_score_mapper)

        self._icx_context_db.write_batch(context, state_wal)
        context.storage.icx.set_last_block(precommit_data.block_batch.block)
        context.engine.inv.commit(context, precommit_data)
        self._precommit_data_manager.commit(precommit_data.block_batch.block)

    @staticmethod
    def _process_iiss_commit(context: 'IconScoreContext',
                             precommit_data: 'PrecommitData',
                             iiss_wal: Optional['IissWAL'],
                             is_calc_period_start_block: bool) -> Optional['RewardCalcDBInfo']:
        """Assume that this method is called after Revision.IISS is on

        :param context:
        :param precommit_data:
        :param iiss_wal:
        :param is_calc_period_start_block:
        :return:
        """
        assert precommit_data.revision >= Revision.IISS.value
        assert isinstance(iiss_wal, IissWAL)
        calc_end_block_height: int = -1
        standby_db_info: Optional['RewardCalcDBInfo'] = None

        if is_calc_period_start_block:
            calc_end_block_height: int = context.block.height - 1
            standby_db_info: 'RewardCalcDBInfo' = context.storage.rc.replace_db(calc_end_block_height)

        context.engine.prep.commit(context, precommit_data)
        context.storage.rc.commit(iiss_wal)

        if is_calc_period_start_block:
            RewardCalcStorage.finalize_iiss_db(calc_end_block_height,
                                               context.storage.rc.key_value_db,
                                               standby_db_info.path)
        return standby_db_info

    @staticmethod
    def _process_ipc(context: 'IconScoreContext',
                     wal_writer: 'WriteAheadLogWriter',
                     precommit_data: 'PrecommitData',
                     standby_db_info: Optional['RewardCalcDBInfo'],
                     instant_block_hash: bytes):
        assert precommit_data.revision >= Revision.IISS.value

        commit_block_hash: bytes = precommit_data.block.hash
        if commit_block_hash != instant_block_hash:
            # Leader node must use instant_block_hash which is used in invoke()
            commit_block_hash: bytes = instant_block_hash

        context.engine.iiss.send_commit(
            precommit_data.block.height, commit_block_hash)
        wal_writer.write_state(WALState.SEND_COMMIT_BLOCK.value, add=True)
        wal_writer.flush()

        if standby_db_info is not None:
            iiss_db_path: str = context.storage.rc.rename_standby_db_to_iiss_db(standby_db_info.path)
            context.engine.iiss.send_calculate(iiss_db_path, standby_db_info.block_height)
            wal_writer.write_state(WALState.SEND_CALCULATE.value, add=True)

    def rollback(self, block_height: int, block_hash: bytes) -> dict:
        """Rollback the current confirmed state to the old one indicated by block_height

        :param block_height: final block height after rollback
        :param block_hash: final block hash after rollback
        :return:
        """
        Logger.info(tag=ROLLBACK_LOG_TAG,
                    msg=f"rollback() start: height={block_height} hash={bytes_to_hex(block_hash)}")

        last_block: 'Block' = self._get_last_block()
        Logger.info(tag=_TAG, msg=f"last_block={last_block}")

        # If rollback is not possible for the current state,
        # self._is_rollback_needed() should raise an InternalServiceErrorException
        try:
            if self._is_rollback_needed(last_block, block_height, block_hash):
                # Get the start block height of this term
                term_start_block_height: int = IconScoreContext.engine.prep.term.start_block_height

                # Record rollback metadata
                path = self._get_rollback_metadata_path()
                metadata = RollbackMetadata(
                    block_height, block_hash, term_start_block_height, last_block)
                metadata.save(path)

                # Do rollback
                context = self._context_factory.create(IconScoreContextType.DIRECT, block=last_block)
                self._rollback(context, block_height, block_hash, term_start_block_height)

                self._remove_rollback_metadata()

        except BaseException as e:
            Logger.error(tag=ROLLBACK_LOG_TAG, msg=str(e))
            raise InternalServiceErrorException(
                f"Failed to rollback: {last_block.height} -> {block_height}")

        response = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.BLOCK_HASH: block_hash
        }

        Logger.info(tag=ROLLBACK_LOG_TAG, msg=f"rollback() end")

        return response

    def _is_rollback_needed(self, last_block: 'Block', block_height: int, block_hash: bytes) -> bool:
        """Check if rollback is needed
        """
        if block_height == last_block.height and block_hash == last_block.hash:
            # No need to rollback
            return False

        if check_backup_exists(self._backup_root_path, last_block.height, block_height):
            # There are enough backup files to rollback
            return True

        raise InternalServiceErrorException(
            f"Failed to rollback: "
            f"height={block_height} "
            f"hash={bytes_to_hex(block_hash)} "
            f"last_block={last_block}")

    def _rollback(self, context: 'IconScoreContext',
                  rollback_block_height: int,
                  rollback_block_hash: bytes,
                  term_start_block_height: int):
        """

        :param context:
        :param rollback_block_height: final block_height after rollback
        :param rollback_block_hash: final block hash after rollback
        """
        # Close storage
        IconScoreContext.storage.rc.close()

        # Rollback state_db and rc_data_db to those of a given block_height
        rollback_manager = RollbackManager(
            self._backup_root_path, self._rc_data_path, self._icx_context_db.key_value_db)
        rollback_manager.run(
            last_block_height=context.block.height,
            rollback_block_height=rollback_block_height,
            term_start_block_height=term_start_block_height)

        # Rollback the state of reward_calculator prior to iconservice
        IconScoreContext.engine.iiss.rollback_reward_calculator(rollback_block_height, rollback_block_hash)

        # Clear all iconscores and reload builtin scores only
        builtin_score_owner: 'Address' = Address.from_string(self._conf[ConfigKey.BUILTIN_SCORE_OWNER])
        self._load_builtin_scores(context, builtin_score_owner)

        # Rollback storages
        storages = [
            IconScoreContext.storage.deploy,
            IconScoreContext.storage.fee,
            IconScoreContext.storage.icx,
            IconScoreContext.storage.iiss,
            IconScoreContext.storage.prep,
            IconScoreContext.storage.issue,
            IconScoreContext.storage.meta,
            IconScoreContext.storage.rc,
        ]
        for storage in storages:
            storage.rollback(context, rollback_block_height, rollback_block_hash)

        # Rollback engines to block_height
        engines = [
            IconScoreContext.engine.deploy,
            IconScoreContext.engine.fee,
            IconScoreContext.engine.icx,
            IconScoreContext.engine.iiss,
            IconScoreContext.engine.prep,
            IconScoreContext.engine.issue,
        ]
        for engine in engines:
            engine.rollback(context, rollback_block_height, rollback_block_hash)

        # Reset last_block
        self._init_last_block_info(context)

    def clear_context_stack(self):
        """Clear IconScoreContext stacks
        """
        stack_size: int = self._get_context_stack_size()
        assert stack_size == 0

        if stack_size > 0:
            Logger.error(f'IconScoreContext leak is detected: {stack_size}', _TAG)

        self._clear_context()

    def _get_last_block(self) -> Optional['Block']:
        return self._precommit_data_manager.last_block

    def inner_call(self, request: dict):
        context: 'IconScoreContext' = self._context_factory.create(
            IconScoreContextType.QUERY, block=self._get_last_block()
        )

        return inner_call(context, request)

    def _recover_dbs(self, rc_data_path: str):
        """
        CAUTION: last_block_info is not ready at this moment

        """

        self._recover_commit(rc_data_path)
        self._recover_rollback()

    def _recover_rollback(self):
        Logger.debug(tag=ROLLBACK_LOG_TAG, msg=f"_recover_rollback() start")

        # Load RollbackMetadata from a file
        path = self._get_rollback_metadata_path()
        metadata: Optional['RollbackMetadata'] = RollbackMetadata.load(path)

        if metadata:
            # Resume the previous rollback for the databases managed by iconservice
            rollback_manager = RollbackManager(
                self._backup_root_path, self._rc_data_path, self._icx_context_db.key_value_db)
            rollback_manager.run(
                last_block_height=metadata.last_block.height,
                rollback_block_height=metadata.block_height,
                term_start_block_height=metadata.term_start_block_height)

        Logger.debug(tag=WAL_LOG_TAG, msg=f"_recover_rollback() end")

    def _recover_commit(self, rc_data_path: str):
        """Recover iiss_db and state_db with a wal file

        :param rc_data_path: The directory where iiss_dbs are contained
        """

        Logger.debug(tag=WAL_LOG_TAG, msg=f"_recover_commit() start: rc_data_path={rc_data_path}")

        path: str = self._get_write_ahead_log_path()
        if not os.path.isfile(path):
            Logger.debug(tag=WAL_LOG_TAG, msg=f"_recover_commit() end: No WAL file {path}")
            return

        self._wal_reader = None
        reader = WriteAheadLogReader()
        try:
            reader.open(path)
            Logger.info(tag=WAL_LOG_TAG, msg=f"reader=({reader})")

            if reader.log_count == 2:
                self._recover_rc_db(reader, rc_data_path)
                self._recover_state_db(reader)
                self._wal_reader = reader
            else:
                Logger.debug(tag=WAL_LOG_TAG, msg=f"Incomplete WAL file: {path}")
        except IconServiceBaseException as e:
            Logger.info(tag=WAL_LOG_TAG, msg=e.message)
        except BaseException as e:
            Logger.warning(tag=WAL_LOG_TAG, msg=str(e))
        finally:
            reader.close()

        try:
            os.remove(path)
        except BaseException as e:
            Logger.error(tag=WAL_LOG_TAG, msg=str(e))

        Logger.debug(tag=WAL_LOG_TAG, msg="_recover_commit() end")

    @staticmethod
    def _is_need_to_recover_rc_db(wal_state: 'WALState', is_calc_period_start_block: bool) -> bool:
        if wal_state & WALState.WRITE_RC_DB:
            if not is_calc_period_start_block or \
                    (is_calc_period_start_block and wal_state & WALState.SEND_CALCULATE):
                return False

        return True

    @classmethod
    def _recover_rc_db(cls, reader: 'WriteAheadLogReader', rc_data_path: str):
        Logger.debug(tag=WAL_LOG_TAG, msg=f"_recover_rc_db() start: rc_data_path={rc_data_path}")

        wal_state = WALState(reader.state)
        is_calc_period_start_block = bool(wal_state & WALState.CALC_PERIOD_START_BLOCK)
        Logger.info(tag=WAL_LOG_TAG, msg=f"reader state={wal_state}")

        if not cls._is_need_to_recover_rc_db(wal_state, is_calc_period_start_block):
            Logger.info(tag=WAL_LOG_TAG, msg="rc_db has already been up-to-date")
            return

        # If WAL file is made at the start block of calc period
        if is_calc_period_start_block:
            cls._rename_rc_db_on_calc_start_block(rc_data_path, reader.block)

        # Write data to "current_db"
        current_db: 'KeyValueDatabase' = RewardCalcStorage.create_current_db(rc_data_path)
        current_db.write_batch(reader.get_iterator(WALDBType.RC.value))

        # If the block to recover is the start block of this term
        if is_calc_period_start_block:
            calc_end_block_height: int = reader.block.height - 1
            iiss_rc_db_name: str = RewardCalcStorage.get_iiss_rc_db_name(calc_end_block_height)
            iiss_rc_db_path: str = os.path.join(rc_data_path, iiss_rc_db_name)
            RewardCalcStorage.finalize_iiss_db(calc_end_block_height, current_db, iiss_rc_db_path)
        current_db.close()

        Logger.debug(tag=WAL_LOG_TAG, msg="_recover_rc_db() end")

    @classmethod
    def _rename_rc_db_on_calc_start_block(cls, rc_data_path: str, block: 'Block'):
        class DBType(IntEnum):
            CURRENT = 0
            STANDBY = 1
            IISS = 2

        calc_end_block_height = block.height - 1

        items = (
            [RewardCalcStorage.CURRENT_IISS_DB_NAME, False],
            [RewardCalcStorage.get_standby_rc_db_name(calc_end_block_height), False],
            [RewardCalcStorage.get_iiss_rc_db_name(calc_end_block_height), False]
        )

        for item in items:
            item[0]: str = os.path.join(rc_data_path, item[0])
            item[1]: bool = os.path.isdir(item[0])

        if items[DBType.IISS][1]:
            # Do nothing
            pass
        elif items[DBType.STANDBY][1]:
            # Rename standby_rc_db to iiss_rc_db
            shutil.move(items[DBType.STANDBY][0], items[DBType.IISS][0])
        elif items[DBType.CURRENT][1]:
            # Rename current_db to iiss_rc_db
            path: str = items[DBType.CURRENT][0]
            shutil.move(path, items[DBType.IISS][0])
        else:
            raise DatabaseException("IISS-related DB not found")

    def _recover_state_db(self, reader: 'WriteAheadLogReader'):
        Logger.debug(tag=WAL_LOG_TAG, msg=f"_recover_state_db() start: reader={reader}")

        wal_state = WALState(reader.state)
        if wal_state & WALState.WRITE_STATE_DB:
            Logger.info(tag=WAL_LOG_TAG, msg="state_db has already been up-to-date")
            return

        ret: int = self._icx_context_db.key_value_db.write_batch(reader.get_iterator(WALDBType.STATE.value))
        Logger.info(tag=WAL_LOG_TAG, msg=f"state_db has been updated with wal file: count={ret}")

        Logger.debug(tag=WAL_LOG_TAG, msg="_recover_state_db() end")

    def _get_write_ahead_log_path(self) -> str:
        return os.path.join(self._state_db_root_path, self.WAL_FILE)

    def _get_rollback_metadata_path(self) -> str:
        return os.path.join(self._state_db_root_path, self.ROLLBACK_METADATA_FILE)

    def _remove_rollback_metadata(self):
        Logger.debug(tag=ROLLBACK_LOG_TAG, msg="_remove_rollback_metadata() start")

        path = self._get_rollback_metadata_path()
        try:
            os.remove(path)
            Logger.info(tag=ROLLBACK_LOG_TAG, msg=f"Remove {path}")
        except:
            Logger.error(tag=ROLLBACK_LOG_TAG, msg=f"Failed to remove {path}")

        Logger.debug(tag=ROLLBACK_LOG_TAG, msg="_remove_rollback_metadata() end")

    def hello(self) -> dict:
        """If state_db and rc_db are recovered, send COMMIT_BLOCK message to reward calculator
        It is called on INVOKE thread
        Assume that the connection between iconservice and rc is ready

        :return:
        """
        Logger.debug(tag=_TAG, msg="hello() start")

        self._finish_to_recover_commit()
        self._finish_to_recover_rollback()

        Logger.debug(tag=_TAG, msg="hello() end")

        return {}

    def _finish_to_recover_commit(self):
        """Finish to recover WAL by sending COMMIT_BLOCK message to reward calculator
        """
        Logger.debug(tag=_TAG, msg="_finish_to_recover_commit() start")

        if not isinstance(self._wal_reader, WriteAheadLogReader):
            Logger.debug(tag=_TAG, msg="_finish_to_recover_commit() end")
            return

        iiss_engine: 'IISSEngine' = IconScoreContext.engine.iiss
        last_block: 'Block' = self._get_last_block()

        wal_state = WALState(self._wal_reader.state)

        # If only writing rc_db is done on commit without sending COMMIT_BLOCK to rc,
        # send COMMIT_BLOCK to rc prior to invoking a block
        if not (wal_state & WALState.SEND_COMMIT_BLOCK):
            iiss_engine.send_commit(
                self._wal_reader.block.height, self._wal_reader.instant_block_hash)

        assert last_block == self._wal_reader.block

        # No need to use
        self._wal_reader = None

        Logger.debug(tag=_TAG, msg="_finish_to_recover_commit() end")

    def _finish_to_recover_rollback(self):
        """Finish to recover rollback by sending ROLLBACK message to reward calculator
        """
        Logger.debug(tag=_TAG, msg="_finish_to_recover_rollback() start")

        # Get ROLLBACK_METADATA file path
        path = self._get_rollback_metadata_path()

        # Load RollbackMetadata from a file
        metadata: Optional[RollbackMetadata] = RollbackMetadata.load(path)

        if metadata:
            # Request reward calculator to rollback its state
            IconScoreContext.engine.iiss.rollback_reward_calculator(metadata.block_height, metadata.block_hash)

            # Remove ROLLBACK_METADATA file when the rollback is done.
            self._remove_rollback_metadata()

            # Remove obsolete block backup files used for rollback
            self._backup_cleaner.run(
                start_block_height=metadata.block_height + 1,
                end_block_height=metadata.last_block.height - 1)

        Logger.debug(tag=_TAG, msg="_finish_to_recover_rollback() end")

    def _set_block_invoke_timeout(self, conf: Dict[str, Union[str, int]]):
        try:
            timeout_s: int = conf[ConfigKey.BLOCK_INVOKE_TIMEOUT]
            if timeout_s > 0:
                self._block_invoke_timeout_s = timeout_s
        except:
            pass

        Logger.info(tag=_TAG, msg=f"{ConfigKey.BLOCK_INVOKE_TIMEOUT}: {self._block_invoke_timeout_s}")

    def _continue_to_invoke(self, tx_request: Dict, tx_timer: 'Timer') -> bool:
        """If this is a block created by a leader,
        check to continue transaction invoking with block_invoke_timeout

        :param tx_request:
        :param tx_timer:
        :return:
        """
        to: Optional['Address'] = tx_request["params"].get("to")

        # Skip EOA to EOA coin transfer in execution time check
        if to and to.is_contract:
            if tx_timer.duration >= self._block_invoke_timeout_s:
                Logger.info(
                    tag=_TAG,
                    msg=f"Stop transaction invoking: "
                        f"duration={tx_timer.duration} "
                        f"block_invoke_timeout={self._block_invoke_timeout_s}"
                )
                return False

        return True

    def _run_unstake_patcher(self, context: 'IconScoreContext'):
        Logger.info(tag=_TAG, msg="_run_unstake_patcher() start")

        if context.revision == Revision.FIX_BALANCE_BUG.value:
            try:
                path: Optional[str] = self._conf.get(
                    ConfigKey.INVALID_EXPIRED_UNSTAKES_PATH, None)
                Logger.info(tag="UNSTAKE", msg=f"path: {path}")

                patcher = UnstakePatcher.from_path(path)
                patcher.run(context)

                names: List[str] = INVALID_EXPIRED_UNSTAKES_FILENAME.split(".")
                report_path: str = os.path.join(self._log_dir, f"{names[0]}_report.json")
                patcher.write_result(report_path)
            except BaseException as e:
                Logger.exception(tag=_TAG, msg=f"Failed to run UnstakePatcher: {str(e)}")
        else:
            Logger.exception(
                tag=_TAG,
                msg="Failed to run unstake_patcher: "
                    f"revision({context.revision}) != {Revision.FIX_BALANCE_BUG.value}"
            )

        Logger.info(tag=_TAG, msg="_run_unstake_patcher() end")

    @classmethod
    def _handle_debug_get_account(
            cls,
            context: 'IconScoreContext',
            params: dict
    ) -> dict:
        """
        Handles get raw data of account in StateDB

        :param context: context
        :param params: parameters of account address and filter
        :return: account raw data of stateDB
        """

        address: 'Address' = params["address"]
        account_filter: 'AccountPartFlag' = AccountPartFlag(params["filter"])
        raw_data: dict = context.engine.icx.get_account_raw_data(
            context=context,
            address=address,
            account_filter=account_filter
        )
        return raw_data
