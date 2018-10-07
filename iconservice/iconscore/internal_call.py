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

from iconservice.base.exception import InvalidRequestException
from ..icon_constant import ICX_TRANSFER_EVENT_LOG, MAX_CALL_STACK_SIZE, IconScoreFuncType
from .icon_score_event_log import EventLogEmitter
from .icon_score_step import StepType
from .icon_score_trace import Trace, TraceType
from ..base.address import Address
from ..base.message import Message

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from ..icx.icx_engine import IcxEngine


class InternalCall(object):
    icx_engine: 'IcxEngine' = None

    def __init__(self, context: 'IconScoreContext'):
        self.__context = context

    def get_icx_balance(self, address: 'Address') -> int:
        return self.icx_engine.get_balance(self.__context, address)

    def icx_transfer_call(self, addr_from: 'Address', addr_to: 'Address', amount: int) -> None:
        """transfer icx to the given 'addr_to'
        If failed, an exception will be raised

        :param addr_from: icx sender address
        :param addr_to: icx receiver address
        :param amount: the amount of icx to transfer
        """
        self._call(addr_from, addr_to, None, (), {}, amount)

    def other_external_call(self,
                            addr_from: 'Address',
                            addr_to: 'Address',
                            func_name: str,
                            arg_params: tuple,
                            kw_params: dict,
                            amount: int) -> Any:
        return self._call(addr_from, addr_to, func_name, arg_params, kw_params, amount)

    def _call(self,
              addr_from: 'Address',
              addr_to: 'Address',
              func_name: Optional[str],
              arg_params: tuple,
              kw_params: dict,
              amount: int) -> Any:

        self.__context.enter_call()

        try:
            self._make_trace(addr_from, addr_to, func_name, arg_params, kw_params, amount)

            self.__context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)

            self.icx_engine.transfer(self.__context, addr_from, addr_to, amount)

            if amount > 0:
                self.emit_event_log_for_icx_transfer(addr_from, addr_to, amount)

            if addr_to.is_contract:
                return self._other_score_call(addr_from, addr_to, func_name, arg_params, kw_params, amount)

            return None
        except BaseException as e:
            self.__context.revert_call()
            raise e
        finally:
            self.__context.leave_call()

    def _make_trace(self,
                    _from: 'Address',
                    _to: 'Address',
                    func_name: Optional[str],
                    arg_params: tuple,
                    kw_params: dict,
                    amount: int) -> None:
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
        self.__context.traces.append(trace)

    def _other_score_call(self,
                          addr_from: Address,
                          addr_to: 'Address',
                          func_name: Optional[str],
                          arg_params: tuple,
                          kw_params: dict,
                          amount: int) -> Any:
        """Call the functions provided by other icon scores.

        :param addr_from:
        :param addr_to:
        :param func_name:
        :param arg_params:
        :param kw_params:
        :param amount:
        :return:
        """

        self.__context.validate_score_blacklist(addr_to)

        if len(self.__context.msg_stack) == MAX_CALL_STACK_SIZE:
            raise InvalidRequestException('Max call stack size exceeded')

        self.__context.msg_stack.append(self.__context.msg)

        self.__context.msg = Message(sender=addr_from, value=amount)
        self.current_address = addr_to

        prev_func_type = self.__context.func_type
        try:
            icon_score = self.__context.get_icon_score(addr_to)
            is_func_readonly = getattr(icon_score, '_IconScoreBase__is_func_readonly')
            if func_name is not None and is_func_readonly(func_name):
                self.__context.func_type = IconScoreFuncType.READONLY
            else:
                self.__context.func_type = IconScoreFuncType.WRITABLE

            if func_name is None:
                fallback_func = getattr(icon_score, '_IconScoreBase__fallback_call')
                fallback_func()
                return None
            else:
                external_func = getattr(icon_score, '_IconScoreBase__external_call')
                return external_func(func_name=func_name, arg_params=arg_params, kw_params=kw_params)
        except BaseException as e:
            raise e
        finally:
            self.__context.func_type = prev_func_type
            self.current_address = addr_from
            self.__context.msg = self.__context.msg_stack.pop()

    def emit_event_log_for_icx_transfer(self, from_: 'Address', to: 'Address', value: int):
        event_signature = ICX_TRANSFER_EVENT_LOG
        arguments = [from_, to, value]
        indexed_args_count = 3
        EventLogEmitter.emit_event_log(
            self.__context, from_, event_signature, arguments, indexed_args_count)
