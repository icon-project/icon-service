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

from .icon_score_trace import Trace
from ..base.block import Block
from ..base.exception import FatalException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import (
    IconScoreContextType, IconScoreFuncType, REV_DECENTRALIZATION,
    PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
)

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_event_log import EventLog
    from .icon_score_mapper import IconScoreMapper
    from .icon_score_step import IconScoreStepCounter
    from ..base.address import Address
    from ..prep.data.prep_container import PRep, PRepContainer
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
    score_root_path: str = None
    icon_score_mapper: 'IconScoreMapper' = None
    icon_service_flag: int = 0
    legacy_tbears_mode: bool = False
    iiss_initial_irep: int = 0

    engine: 'ContextEngine' = None
    storage: 'ContextStorage' = None

    main_prep_count: int = PREP_MAIN_PREPS
    main_and_sub_prep_count: int = PREP_MAIN_AND_SUB_PREPS

    decentralize_trigger: float = 0

    """Contains the useful information to process user's JSON-RPC request
    """

    def __init__(self, context_type: 'IconScoreContextType' = IconScoreContextType.QUERY) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        """
        self.type: 'IconScoreContextType' = context_type
        # The type of external function which is called latest
        self.func_type: 'IconScoreFuncType' = IconScoreFuncType.WRITABLE
        self.block: 'Block' = None
        self.tx: 'Transaction' = None
        self.msg: 'Message' = None
        self.current_address: 'Address' = None
        self.revision: int = 0
        self.block_batch: 'BlockBatch' = None
        self.tx_batch: 'TransactionBatch' = None
        self.rc_block_batch: list = []
        self.rc_tx_batch: list = []
        self.new_icon_score_mapper: 'IconScoreMapper' = None
        self.cumulative_step_used: int = 0
        self.step_counter: 'IconScoreStepCounter' = None
        self.event_logs: List['EventLog'] = None
        self.traces: List['Trace'] = None
        self.fee_sharing_proportion = 0  # The proportion of fee by SCORE in percent (0-100)

        self.msg_stack = []
        self.event_log_stack = []

        # PReps to update on invoke
        self.preps: Optional['PRepContainer'] = None
        self.tx_dirty_preps: Optional[OrderedDict['Address', 'PRep']] = None

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

    def is_decentralized(self) -> bool:
        return self.revision >= REV_DECENTRALIZATION and self.engine.prep.term.sequence != -1

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
        """Update context.preps when a tx is done

        Caution: call update_dirty_prep_batch before update_state_db_batch()
        """
        for dirty_prep in self.tx_dirty_preps.values():
            self.preps.replace(dirty_prep)
            # Write serialized dirty_prep data into tx_batch
            self.storage.prep.put_prep(self, dirty_prep)
            dirty_prep.freeze()

        self.tx_dirty_preps.clear()

    def clear_batch(self):
        if self.tx_batch:
            self.tx_batch.clear()
        if self.rc_tx_batch:
            self.rc_tx_batch.clear()
        if self.tx_dirty_preps:
            self.tx_dirty_preps.clear()

    def get_prep(self, address: 'Address', mutable: bool = False) -> Optional['PRep']:
        prep: 'PRep' = self.tx_dirty_preps.get(address)
        if prep is None:
            prep = self.preps.get_by_address(address)

        if prep and prep.is_frozen() and mutable:
            prep = prep.copy()

        return prep

    def put_dirty_prep(self, prep: 'PRep'):
        self.tx_dirty_preps[prep.address] = prep
