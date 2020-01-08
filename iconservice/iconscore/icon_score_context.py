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

import threading
import warnings
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, List

from iconcommons.logger import Logger

from .icon_score_mapper import IconScoreMapper
from .icon_score_trace import Trace
from ..base.block import Block
from ..base.exception import FatalException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import (
    IconScoreContextType, IconScoreFuncType, TERM_PERIOD, PRepGrade, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS,
    Revision, PRepFlag)
from ..icx.issue.regulator import Regulator

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_event_log import EventLog
    from .icon_score_step import IconScoreStepCounter, IconScoreStepCounterFactory
    from ..base.address import Address
    from ..prep.data import PRep, PRepContainer, Term
    from ..utils import ContextEngine, ContextStorage

_thread_local_data = threading.local()


class ContextContainer(object):
    """ContextContainer mixin

    Every class which inherits ContextContainer can share IconScoreContext instance
    in the current thread.
    """

    @staticmethod
    def _get_context() -> Optional['IconScoreContext']:
        context_stack: List['IconScoreContext'] = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack[-1]
        else:
            return None

    @staticmethod
    def _push_context(context: 'IconScoreContext') -> None:
        context_stack: List['IconScoreContext'] = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is None:
            context_stack = []
            setattr(_thread_local_data, 'context_stack', context_stack)

        context_stack.append(context)

    @staticmethod
    def _pop_context() -> 'IconScoreContext':
        """Delete the last pushed context of the current thread
        """
        context_stack: List['IconScoreContext'] = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack.pop()
        else:
            raise FatalException('Failed to pop a context out of context_stack')

    @staticmethod
    def _clear_context() -> None:
        setattr(_thread_local_data, 'context_stack', None)

    @staticmethod
    def _get_context_stack_size() -> int:
        context_stack: List['IconScoreContext'] = getattr(_thread_local_data, 'context_stack', None)
        return 0 if context_stack is None else len(context_stack)


class ContextGetter(object):
    """The class which refers to IconScoreContext should inherit ContextGetter
    """

    @property
    def _context(self) -> 'IconScoreContext':
        return ContextContainer._get_context()


class IconScoreContext(object):
    TAG = "CTX"

    score_root_path: str = None
    icon_score_mapper: 'IconScoreMapper' = None
    icon_service_flag: int = 0
    legacy_tbears_mode: bool = False
    iiss_initial_irep: int = 0

    engine: 'ContextEngine' = None
    storage: 'ContextStorage' = None

    main_prep_count: int = PREP_MAIN_PREPS
    main_and_sub_prep_count: int = PREP_MAIN_AND_SUB_PREPS
    term_period: int = TERM_PERIOD

    decentralize_trigger: float = 0

    precommitdata_log_flag = False
    step_trace_flag: bool = False
    log_level: str = None

    """Contains the useful information to process user's JSON-RPC request
    """

    def __init__(self, context_type: 'IconScoreContextType' = IconScoreContextType.QUERY) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        """
        self.type: 'IconScoreContextType' = context_type
        # The type of external function which is called latest
        self.func_type: 'IconScoreFuncType' = IconScoreFuncType.WRITABLE
        self.block: Optional['Block'] = None
        self.tx: Optional['Transaction'] = None
        self.msg: Optional['Message'] = None
        self.current_address: Optional['Address'] = None
        self.revision: int = 0
        self.block_batch: Optional['BlockBatch'] = None
        self.tx_batch: Optional['TransactionBatch'] = None
        self.rc_block_batch: list = []
        self.rc_tx_batch: list = []
        self.new_icon_score_mapper: Optional['IconScoreMapper'] = None
        self.cumulative_step_used: int = 0
        self.step_counter: Optional['IconScoreStepCounter'] = None
        self.event_logs: Optional[List['EventLog']] = None
        self.traces: Optional[List['Trace']] = None
        self.fee_sharing_proportion = 0  # The proportion of fee by SCORE in percent (0-100)

        self.msg_stack = []
        self.event_log_stack = []

        # PReps to update on invoke
        self._preps: Optional['PRepContainer'] = None
        self._tx_dirty_preps: Optional[OrderedDict['Address', 'PRep']] = None
        # Collect Main and Sub P-Reps which have just been invalidated by penalty or unregister
        # to use for updating term info at the end of invoke
        self._term: Optional['Term'] = None

        self.regulator: Optional['Regulator'] = None

    @classmethod
    def set_decentralize_trigger(cls, decentralize_trigger: float):
        decentralize_trigger: float = decentralize_trigger

        if not 1.0 > decentralize_trigger >= 0:
            raise FatalException(f"Invalid min delegation percent for decentralize: {decentralize_trigger}."
                                 f"Do not exceed 100% or negative value")
        IconScoreContext.decentralize_trigger = decentralize_trigger

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY or self.func_type == IconScoreFuncType.READONLY

    @property
    def total_supply(self):
        return self.storage.icx.get_total_supply(self)

    @property
    def preps(self) -> Optional['PRepContainer']:
        return self._preps

    @property
    def term(self) -> Optional['Term']:
        return self._term

    def is_decentralized(self) -> bool:
        return self.engine.prep.term is not None

    def is_the_first_block_on_decentralization(self) -> bool:
        term = self.engine.prep.term
        return term.sequence == 0 and self.block.height == term.start_block_height

    def set_func_type_by_icon_score(self, icon_score: 'IconScoreBase', func_name: str):
        is_func_readonly = getattr(icon_score, '_IconScoreBase__is_func_readonly')
        if func_name is not None and is_func_readonly(func_name):
            self.func_type = IconScoreFuncType.READONLY
        else:
            self.func_type = IconScoreFuncType.WRITABLE

    # TODO should remove after update GOVERNANCE 0.0.6 afterward
    def deploy(self, tx_hash: bytes) -> None:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        self.engine.deploy.deploy(self, tx_hash)

    def update_batch(self):
        """Called when a transaction is done

        :return:
        """

        # Call update_dirty_prep_batch before update_state_db_batch()
        self.update_dirty_prep_batch()
        self.update_state_db_batch()
        self.update_rc_db_batch()

    def update_state_db_batch(self):
        self.block_batch.update(self.tx_batch)
        self.tx_batch.clear()

    def update_rc_db_batch(self):
        self.rc_block_batch.extend(self.rc_tx_batch)
        self.rc_tx_batch.clear()

    def update_dirty_prep_batch(self):
        """Apply updated P-Rep data to context.preps every time when a tx is done

        Caution: call update_dirty_prep_batch before update_state_db_batch()
        """
        for dirty_prep in self._tx_dirty_preps.values():
            # If dirty_prep is an invalid elected P-Rep,
            # we should update P-Reps in this term
            self._update_elected_preps_in_term(dirty_prep)

            if self.revision >= Revision.REALTIME_P2P_ENDPOINT_UPDATE.value:
                self._update_main_preps_in_term(dirty_prep)

            self._replace_prep(dirty_prep)

            # Write serialized dirty_prep data into tx_batch
            self.storage.prep.put_prep(self, dirty_prep)
            dirty_prep.freeze()

        self._tx_dirty_preps.clear()

    def _replace_prep(self, dirty_prep: 'PRep'):
        """Replace a changed P-Rep instance with the old one in self._preps

        Assume that this method should be called on invoke process

        :param dirty_prep: changed P-Rep instance
        :return:
        """
        assert self.type == IconScoreContextType.INVOKE

        if self._preps.is_frozen():
            # Copy self._preps on demand for performance
            # The copied self._preps is not frozen before calling self._preps.freeze()
            self._preps = self._preps.copy(mutable=True)

        self._preps.replace(dirty_prep)

    def _update_elected_preps_in_term(self, dirty_prep: 'PRep'):
        """Collect main and sub preps which cannot serve as a main and sub prep
        to update the current term at the end of invoke

        :param dirty_prep: dirty prep
        """
        if self._term is None:
            return

        if dirty_prep.is_electable():
            return

        # If dirty_prep is not in term, no need to update elected P-Reps
        if dirty_prep.address not in self._term:
            return

        # Just in case, reset the P-Rep grade one to CANDIDATE
        dirty_prep.grade = PRepGrade.CANDIDATE

        self._term.update_invalid_elected_preps([dirty_prep])

        Logger.info(tag=self.TAG, msg=f"Invalid main and sub prep: {dirty_prep}")

    def _update_main_preps_in_term(self, dirty_prep: 'PRep'):
        """

        :param dirty_prep: dirty prep
        """
        if self._term is None:
            return

        if dirty_prep.is_flags_on(PRepFlag.P2P_ENDPOINT) and \
                self._term.is_main_prep(dirty_prep.address):
            self._term.on_main_prep_p2p_endpoint_updated()

        Logger.info(tag=self.TAG, msg=f"_update_main_prep_endpoint_in_term: {dirty_prep}")

    def clear_batch(self):
        if self.tx_batch:
            self.tx_batch.clear()
        if self.rc_tx_batch:
            self.rc_tx_batch.clear()
        if self._tx_dirty_preps:
            self._tx_dirty_preps.clear()

    def get_prep(self, address: 'Address', mutable: bool = False) -> Optional['PRep']:
        prep: Optional['PRep'] = None

        if self._tx_dirty_preps is not None:
            prep = self._tx_dirty_preps.get(address)

        if prep is None:
            prep = self._preps.get_by_address(address)

        if prep and prep.is_frozen() and mutable:
            prep = prep.copy()

        return prep

    def put_dirty_prep(self, prep: 'PRep'):
        Logger.debug(tag=self.TAG, msg=f"put_dirty_prep() start: {prep}")

        if self._tx_dirty_preps is None:
            Logger.warning(tag=self.TAG, msg="self._tx_dirty_preps is None")
            Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")
            return

        if not prep.is_dirty() and self.revision >= Revision.OPTIMIZE_DIRTY_PREP_UPDATE.value:
            Logger.info(tag=self.TAG, msg=f"No need to update an unchanged P-Rep: revision={self.revision}")
            Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")
            return

        self._tx_dirty_preps[prep.address] = prep

        Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")


class IconScoreContextFactory(object):
    def __init__(self, step_counter_factory: 'IconScoreStepCounterFactory'):
        self.step_counter_factory = step_counter_factory

    def create(self, context_type: 'IconScoreContextType', block: 'Block'):
        context: 'IconScoreContext' = IconScoreContext(context_type)
        context.block = block

        if context_type == IconScoreContextType.DIRECT:
            return context

        self._set_step_counter(context)
        self._set_context_attributes_for_processing_tx(context)

        return context

    @staticmethod
    def _is_step_trace_on(context: 'IconScoreContext') -> bool:
        return context.step_trace_flag and context.type == IconScoreContextType.INVOKE

    def _set_step_counter(self, context: 'IconScoreContext'):
        step_trace_flag = self._is_step_trace_on(context)
        if context.type == IconScoreContextType.ESTIMATION:
            context.step_counter = self.step_counter_factory.create(IconScoreContextType.INVOKE, step_trace_flag)
        else:
            context.step_counter = self.step_counter_factory.create(context.type, step_trace_flag)

    @staticmethod
    def _set_context_attributes_for_processing_tx(context: 'IconScoreContext'):
        if context.type in (IconScoreContextType.INVOKE, IconScoreContextType.ESTIMATION):
            context.block_batch = BlockBatch(Block.from_block(context.block))
            context.tx_batch = TransactionBatch()
            context.new_icon_score_mapper = IconScoreMapper()

            # For P-Rep management
            context._tx_dirty_preps = OrderedDict()
            if context.engine.prep.term:
                context._term = context.engine.prep.term.copy()
        else:
            # Readonly
            context._term = context.engine.prep.term

        # context.engine.prep.preps is a readonly instance
        context._preps = context.engine.prep.preps
