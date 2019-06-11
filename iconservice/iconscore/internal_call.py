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

from typing import TYPE_CHECKING, Optional, Any

from . import system_call_handler
from .icon_score_constant import STR_FALLBACK, ATTR_SCORE_CALL
from .icon_score_context_util import IconScoreContextUtil
from .icon_score_event_log import EventLogEmitter
from .icon_score_step import StepType
from .icon_score_trace import Trace, TraceType
from ..base.address import Address
from ..base.exception import StackOverflowException
from ..base.message import Message
from ..icon_constant import ICX_TRANSFER_EVENT_LOG, MAX_CALL_STACK_SIZE, IconScoreContextType

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext


class InternalCall(object):

    @staticmethod
    def icx_get_balance(context: 'IconScoreContext', address: 'Address') -> int:
        return context.icx_engine.get_balance(context, address)

    @staticmethod
    def other_external_call(context: 'IconScoreContext',
                            addr_from: 'Address',
                            addr_to: 'Address',
                            amount: int,
                            func_name: Optional[str],
                            arg_params: Optional[tuple] = None,
                            kw_params: Optional[dict] = None) -> Any:
        if func_name is None:
            func_name = STR_FALLBACK
        return InternalCall._call(context, addr_from, addr_to, amount, func_name, arg_params, kw_params)

    @staticmethod
    def _call(context: 'IconScoreContext',
              addr_from: 'Address',
              addr_to: 'Address',
              amount: int,
              func_name: str,
              arg_params: Optional[tuple],
              kw_params: Optional[dict]) -> Any:

        InternalCall.enter_call(context)

        try:
            InternalCall._make_trace(context, addr_from, addr_to, amount, func_name, arg_params, kw_params)

            context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)

            context.icx_engine.transfer(context, addr_from, addr_to, amount)

            if amount > 0:
                InternalCall.emit_event_log_for_icx_transfer(context, addr_from, addr_to, amount)

            if addr_to == system_call_handler.SYSTEM_ADDRESS:
                return system_call_handler.handle_system_call(
                    context, addr_from, amount, func_name, arg_params, kw_params)
            elif addr_to.is_contract:
                return InternalCall._other_score_call(
                    context, addr_from, addr_to, amount, func_name, arg_params, kw_params)

            return None
        except BaseException as e:
            InternalCall.revert_call(context)
            raise e
        finally:
            InternalCall.leave_call(context)

    @staticmethod
    def _make_trace(context: 'IconScoreContext',
                    _from: 'Address',
                    _to: 'Address',
                    amount: int,
                    func_name: str,
                    arg_params: Optional[tuple],
                    kw_params: Optional[dict]) -> None:
        if arg_params is None:
            arg_data1 = []
        else:
            arg_data1 = [arg for arg in arg_params]

        if kw_params is None:
            arg_data2 = []
        else:
            arg_data2 = [arg for arg in kw_params.values()]

        arg_data = arg_data1 + arg_data2
        trace = Trace(_from, TraceType.CALL, [_to, func_name, arg_data, amount])
        context.traces.append(trace)

    @staticmethod
    def _other_score_call(context: 'IconScoreContext',
                          addr_from: Address,
                          addr_to: 'Address',
                          amount: int,
                          func_name: str,
                          arg_params: Optional[tuple],
                          kw_params: Optional[dict]) -> Any:
        """Call the functions provided by other icon scores.

        :param context:
        :param addr_from:
        :param addr_to:
        :param func_name:
        :param amount:
        :param arg_params:
        :param kw_params:

        :return:
        """

        IconScoreContextUtil.validate_score_blacklist(context, addr_to)

        if len(context.msg_stack) == MAX_CALL_STACK_SIZE:
            raise StackOverflowException('Max call stack size exceeded')

        context.msg_stack.append(context.msg)

        prev_func_type = context.func_type
        context.current_address = addr_to
        context.msg = Message(sender=addr_from, value=amount)

        try:
            icon_score = IconScoreContextUtil.get_icon_score(context, addr_to)
            context.set_func_type_by_icon_score(icon_score, func_name)
            score_func = getattr(icon_score, ATTR_SCORE_CALL)
            return score_func(func_name=func_name, arg_params=arg_params, kw_params=kw_params)
        finally:
            context.func_type = prev_func_type
            context.current_address = addr_from
            context.msg = context.msg_stack.pop()

    @staticmethod
    def emit_event_log_for_icx_transfer(context: 'IconScoreContext',
                                        from_: 'Address',
                                        to: 'Address',
                                        value: int) -> None:
        event_signature = ICX_TRANSFER_EVENT_LOG
        arguments = [from_, to, value]
        indexed_args_count = 3
        EventLogEmitter.emit_event_log(context, from_, event_signature, arguments, indexed_args_count)

    @staticmethod
    def enter_call(context: 'IconScoreContext') -> None:
        """Start to call external function provided by other SCORE
        """
        if context.type != IconScoreContextType.INVOKE:
            return

        context.tx_batch.enter_call()

        context.event_log_stack.append(context.event_logs)
        context.event_logs = []

    @staticmethod
    def revert_call(context: 'IconScoreContext') -> None:
        """An exception happens during calling an external function provided by other SCORE
        Revert the states changed by this function call
        """
        if context.type != IconScoreContextType.INVOKE:
            return

        context.tx_batch.revert_call()
        context.event_logs.clear()

    @staticmethod
    def leave_call(context: 'IconScoreContext') -> None:
        """Finish to call external function provided by other SCORE
        """
        if context.type != IconScoreContextType.INVOKE:
            return

        context.tx_batch.leave_call()

        prev_event_logs = context.event_log_stack.pop()
        context.event_logs = prev_event_logs + context.event_logs
