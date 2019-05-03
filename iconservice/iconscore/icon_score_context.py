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
from typing import TYPE_CHECKING, Optional, List

from ..base.block import Block
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import IconScoreContextType, IconScoreFuncType
from .icon_score_trace import Trace

if TYPE_CHECKING:
    from ..base.address import Address
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine
    from ..icx.icx_engine import IcxEngine
    from ..fee.fee_engine import FeeEngine
    from .icon_score_base import IconScoreBase
    from .icon_score_event_log import EventLog
    from .icon_score_mapper import IconScoreMapper
    from .icon_score_step import IconScoreStepCounter

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
            raise AssertionError('Failed to pop a context out of context_stack')

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
    icon_score_deploy_engine: 'IconScoreDeployEngine' = None
    icx_engine: 'IcxEngine' = None
    fee_engine: 'FeeEngine' = None
    icon_service_flag: int = 0
    legacy_tbears_mode = False

    """Contains the useful information to process user's JSON-RPC request
    """

    def __init__(self, context_type: 'IconScoreContextType' = IconScoreContextType.QUERY) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        """
        self.type: IconScoreContextType = context_type
        # The type of external function which is called latest
        self.func_type: IconScoreFuncType = IconScoreFuncType.WRITABLE
        self.block: 'Block' = None
        self.tx: 'Transaction' = None
        self.msg: 'Message' = None
        self.current_address: 'Address' = None
        self.revision: int = 0
        self.block_batch: 'BlockBatch' = None
        self.tx_batch: 'TransactionBatch' = None
        self.new_icon_score_mapper: 'IconScoreMapper' = None
        self.cumulative_step_used: int = 0
        self.step_counter: 'IconScoreStepCounter' = None
        self.event_logs: List['EventLog'] = None
        self.traces: List['Trace'] = None
        self.fee_sharing_proportion = 0  # The proportion of fee by SCORE in percent (0-100)

        self.msg_stack = []
        self.event_log_stack = []

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY or \
               self.func_type == IconScoreFuncType.READONLY

    def set_func_type_by_icon_score(self, icon_score: 'IconScoreBase', func_name: str):
        is_func_readonly = getattr(icon_score, '_IconScoreBase__is_func_readonly')
        if func_name is not None and is_func_readonly(func_name):
            self.func_type = IconScoreFuncType.READONLY
        else:
            self.func_type = IconScoreFuncType.WRITABLE

    # TODO should remove after update GOVERNANCE 0.0.6 afterward
    def deploy(self, tx_hash: bytes) -> None:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        self.icon_score_deploy_engine.deploy(self, tx_hash)
