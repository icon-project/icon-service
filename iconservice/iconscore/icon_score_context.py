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

from .icon_score_trace import Trace
from ..base.block import Block
from ..base.exception import ServerErrorException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import IconScoreContextType, IconScoreFuncType

if TYPE_CHECKING:
    from .icon_score_mapper import IconScoreMapper
    from .icon_score_step import IconScoreStepCounter
    from .icon_score_event_log import EventLog
    from ..base.address import Address
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine
    from .icon_score_base import IconScoreBase

_thread_local_data = threading.local()


class ContextContainer(object):
    """ContextContainer mixin

    Every class which inherits ContextContainer can share IconScoreContext instance
    in the current thread.
    """

    @staticmethod
    def _get_context() -> Optional['IconScoreContext']:
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack[-1]
        else:
            return None

    @staticmethod
    def _push_context(context: 'IconScoreContext') -> None:
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is None:
            context_stack = []
            setattr(_thread_local_data, 'context_stack', context_stack)

        context_stack.append(context)

    @staticmethod
    def _pop_context() -> 'IconScoreContext':
        """Delete the last pushed context of the current thread
        """
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack.pop()
        else:
            raise ServerErrorException('Failed to pop a context out of context_stack')

    @staticmethod
    def _clear_context() -> None:
        setattr(_thread_local_data, 'context_stack', None)


class ContextGetter(object):
    """The class which refers to IconScoreContext should inherit ContextGetter
    """

    @property
    def _context(self) -> 'IconScoreContext':
        return ContextContainer._get_context()


class IconScoreContext(object):
    # TODO should remove after update GOVERNANCE 0.0.6 afterward
    icon_score_deploy_engine: 'IconScoreDeployEngine' = None

    """Contains the useful information to process user's jsonrpc request
    """

    def __init__(self,
                 context_type: 'IconScoreContextType' = IconScoreContextType.QUERY,
                 func_type: 'IconScoreFuncType' = IconScoreFuncType.WRITABLE,
                 block: 'Block' = None,
                 tx: 'Transaction' = None,
                 msg: 'Message' = None,
                 block_batch: 'BlockBatch' = None,
                 tx_batch: 'TransactionBatch' = None,
                 new_icon_score_mapper: 'IconScoreMapper' = None) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        :param func_type: IconScoreFuncType (READONLY, WRITABLE)
        :param block:
        :param tx: initial transaction info
        :param msg: message call info
        :param block_batch:
        :param tx_batch:
        """
        self.type: IconScoreContextType = context_type
        # The type of external function which is called latest
        self.func_type: IconScoreFuncType = func_type
        self.block = block
        self.tx = tx
        self.msg = msg
        self.current_address: 'Address' = None
        self.block_batch = block_batch
        self.tx_batch = tx_batch
        self.new_icon_score_mapper = new_icon_score_mapper
        self.cumulative_step_used: int = 0
        self.step_counter: 'IconScoreStepCounter' = None
        self.event_logs: List['EventLog'] = None
        self.traces: List['Trace'] = None

        self.msg_stack = []
        self.event_log_stack = []
        self.internal_call_current_address = None

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY or \
               self.func_type == IconScoreFuncType.READONLY

    def clear(self) -> None:
        """Set instance member variables to None
        """
        self.block = None
        self.tx = None
        self.msg = None
        self.block_batch = None
        self.tx_batch = None
        self.new_icon_score_mapper = None
        self.cumulative_step_used = 0
        self.step_counter = None
        self.event_logs = None
        self.traces = None
        self.func_type = IconScoreFuncType.WRITABLE

        self.msg_stack.clear()
        self.event_log_stack.clear()
        self.internal_call_current_address = None

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


class IconScoreContextFactory(object):
    """IconScoreContextFactory
    """

    def __init__(self, max_size: int) -> None:
        """Constructor
        """
        self._lock = threading.Lock()
        self._queue = []
        self._max_size = max_size

    def create(self,
               context_type: 'IconScoreContextType') -> 'IconScoreContext':
        with self._lock:
            if len(self._queue) > 0:
                context = self._queue.pop()
                context.type = context_type
            else:
                context = IconScoreContext(context_type)

        return context

    def destroy(self, context: 'IconScoreContext') -> None:
        with self._lock:
            if len(self._queue) < self._max_size:
                context.clear()
                self._queue.append(context)
