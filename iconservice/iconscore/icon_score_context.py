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

import threading
from enum import IntEnum, unique
from typing import TYPE_CHECKING, Optional, Union, List, Any

from .icon_score_trace import Trace, TraceType
from .icon_score_step import StepType
from ..base.address import Address, GOVERNANCE_SCORE_ADDRESS
from ..base.block import Block
from ..base.exception import IconScoreException, ExceptionCode, ServerErrorException
from ..base.exception import RevertException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icx.icx_engine import IcxEngine
from ..utils.bloom import BloomFilter

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_mapper import IconScoreMapper
    from .icon_score_step import IconScoreStepCounter
    from .icon_score_event_log import EventLog
    from ..deploy.icon_score_manager import IconScoreManager

_thread_local_data = threading.local()


class ContextContainer(object):
    """ContextContainer mixin

    Every class which inherits ContextContainer can share IconScoreContext instance
    in the current thread.
    """

    @staticmethod
    def _get_context() -> 'IconScoreContext':
        return getattr(_thread_local_data, 'context', None)

    @staticmethod
    def _put_context(value: 'IconScoreContext') -> None:
        setattr(_thread_local_data, 'context', value)

    @staticmethod
    def _delete_context(context: 'IconScoreContext') -> None:
        """Delete the context of the current thread
        """
        if context is not _thread_local_data.context:
            raise IconScoreException(
                'Critical error in context management')

        del _thread_local_data.context


class ContextGetter(object):
    """The class which refers to IconScoreContext should inherit ContextGetter
    """

    @property
    def _context(self) -> 'IconScoreContext':
        return getattr(_thread_local_data, 'context', None)


@unique
class IconScoreContextType(IntEnum):
    # Write data to db directly
    DIRECT = 0
    # Record data to cache and after confirming the block, write them to db
    INVOKE = 1
    # Not possible to write data to db
    QUERY = 2


@unique
class IconScoreFuncType(IntEnum):
    # ReadOnly function
    READONLY = 0
    # Writable function
    WRITABLE = 1


class IconScoreContext(object):
    """Contains the useful information to process user's jsonrpc request
    """
    icx_engine: 'IcxEngine' = None
    icon_score_mapper: 'IconScoreMapper' = None
    icon_score_manager: 'IconScoreManager' = None

    def __init__(self,
                 context_type: IconScoreContextType = IconScoreContextType.QUERY,
                 func_type: IconScoreFuncType = IconScoreFuncType.WRITABLE,
                 block: 'Block' = None,
                 tx: 'Transaction' = None,
                 msg: 'Message' = None,
                 block_batch: 'BlockBatch' = None,
                 tx_batch: 'TransactionBatch' = None,
                 new_icon_score_mapper: 'icon_score_mapper' = None) -> None:
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
        self.current_address: Address = None
        self.block_batch = block_batch
        self.tx_batch = tx_batch
        self.new_icon_score_mapper = new_icon_score_mapper
        self.cumulative_step_used: int = 0
        self.step_counter: 'IconScoreStepCounter' = None
        self.event_logs: List['EventLog'] = None
        self.logs_bloom: BloomFilter = None
        self.traces: List['Trace'] = None

        self.__msg_stack = []

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY

    # def gasleft(self) -> int:
    #     """Returns the amount of gas left
    #
    #     If gasleft is zero before tx handling is complete,
    #     rollback all changed state for the tx
    #     Consumed gas doesn't need to be paid back to tx owner.
    #
    #     :return: the amount of gas left
    #     """
    #     raise NotImplementedError()

    def get_balance(self, address: 'Address') -> int:
        """Returns the icx balance of context owner (icon score)

        :return: the icx amount of balance
        """
        return self.icx_engine.get_balance(self, address)

    def internal_call(self,
                      trace_type: 'TraceType',
                      addr_from: 'Address',
                      addr_to: 'Address',
                      func_name: Optional[str],
                      arg_params: Optional[list],
                      kw_params: Optional[dict],
                      icx_value: int,
                      is_exc_handling: bool = False) -> Any:

        self._make_trace(trace_type, addr_from, addr_to, func_name, arg_params, kw_params, icx_value)

        if icx_value > 0 or addr_to.is_contract:
            self.step_counter.apply_step(StepType.CONTRACT_CALL, 1)

        if trace_type == TraceType.CALL:
            ret = self._call(addr_from, addr_to, func_name, arg_params, kw_params, icx_value)
        elif trace_type == TraceType.TRANSFER:
            ret = self._transfer(addr_from, addr_to, icx_value, is_exc_handling)
            if addr_to.is_contract:
                self._call(addr_from, addr_to, None, [], {}, icx_value)
        else:
            ret = None
        return ret

    def _make_trace(self,
                    trace_type: 'TraceType',
                    _from: 'Address',
                    _to: 'Address',
                    func_name: Optional[str],
                    arg_params: Optional[list],
                    kw_params: Optional[dict],
                    icx_value: int) -> None:
        if arg_params is None:
            arg_data1 = []
        else:
            arg_data1 = [arg for arg in arg_params]

        if kw_params is None:
            arg_data2 = []
        else:
            arg_data2 = [arg for arg in kw_params.values()]

        arg_data = arg_data1 + arg_data2
        trace = Trace(_from, trace_type, [_to, func_name, arg_data, icx_value])
        self.traces.append(trace)

    def _transfer(self, addr_from: 'Address', addr_to: 'Address', icx_value: int, is_exc_handling: bool) -> bool:
        ret = None
        try:
            ret = self.icx_engine.transfer(self, addr_from, addr_to, icx_value)
        except BaseException as e:
            if is_exc_handling:
                pass
            else:
                raise e
        return ret

    def _call(self, addr_from: Address,
              addr_to: 'Address', func_name: Optional[str], arg_params: Optional[list], kw_params: Optional[dict],
              icx_value: int) -> object:
        """Call the functions provided by other icon scores.

        :param addr_from:
        :param addr_to:
        :param func_name:
        :param arg_params:
        :param kw_params:
        :param icx_value:
        :return:
        """

        self._validate_score_blacklist(addr_to)
        self.__msg_stack.append(self.msg)

        self.msg = Message(sender=addr_from, value=icx_value)
        self.current_address = addr_to
        icon_score = self.get_icon_score(addr_to)

        ret = call_method(icon_score=icon_score, func_name=func_name,
                          addr_from=addr_from, arg_params=arg_params, kw_params=kw_params)

        self.current_address = addr_from
        self.msg = self.__msg_stack.pop()

        return ret

    def _validate_score_blacklist(self, address: 'Address'):
        if address == GOVERNANCE_SCORE_ADDRESS:
            return

        governance = self.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
        if governance and governance.isInScoreBlackList(address):
            raise ServerErrorException(f'The Score is in Black List (address: {address})')

    # def self_destruct(self, recipient: 'Address') -> None:
    #     """Destroy the current icon score, sending its funds to the given address
    #
    #     :param recipient: fund recipient
    #     """

    def revert(self, message: Optional[str], code: Union[ExceptionCode, int]) -> None:
        """Abort score execution and revert state changes

        :param message: error log message
        :param code:
        """
        raise RevertException(message, code)

    def clear_msg_stack(self):
        self.__msg_stack.clear()

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
        self.logs_bloom = None
        self.traces = None
        self.clear_msg_stack()

    def get_icon_score(self,
                       address: 'Address') -> Optional['IconScoreBase']:
        score = None
        if self.type == IconScoreContextType.INVOKE:
            if self.new_icon_score_mapper is not None:
                score = self.new_icon_score_mapper.get_icon_score(self, address)
        if score is None:
            score = self.icon_score_mapper.get_icon_score(self, address)
        return score


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


ATTR_CALL_METHOD = '_IconScoreBase__call_method'
ATTR_CALL_FALLBACK = '_IconScoreBase__call_fallback'


def call_method(icon_score: 'IconScoreBase', func_name: Optional[str], kw_params: dict,
                addr_from: Optional['Address'] = None, arg_params: list = None) -> Any:
    __check_call_score_invalid(icon_score, addr_from)

    if func_name is None:
        call_fallback_func = getattr(icon_score, ATTR_CALL_FALLBACK)
        call_fallback_func()
    else:
        call_method_func = getattr(icon_score, ATTR_CALL_METHOD)
        if arg_params is None:
            arg_params = []
        if kw_params is None:
            kw_params = {}
        need_type_convert = addr_from is None
        return call_method_func(func_name, arg_params, kw_params, need_type_convert)


def __check_call_score_invalid(icon_score: 'IconScoreBase', addr_from: Optional['Address']) -> None:
    if icon_score is None:
        raise IconScoreException('score is None')

    if __check_myself(addr_from, icon_score.address):
        raise IconScoreException("call function myself")


def __check_myself(addr_from: Optional['Address'], addr_to: 'Address') -> bool:
    return addr_from == addr_to
