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

from .icon_score_step import StepType
from .icon_score_trace import Trace, TraceType
from ..base.address import Address, GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ServerErrorException
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

    def icx_send_call(self, addr_from: 'Address', addr_to: 'Address', amount: int) -> bool:
        return self._call(TraceType.TRANSFER, addr_from, addr_to, None, (), {}, amount, True)

    def icx_transfer_call(self, addr_from: 'Address', addr_to: 'Address', amount: int) -> bool:
        return self._call(TraceType.TRANSFER, addr_from, addr_to, None, (), {}, amount)

    def other_external_call(self,
                            addr_from: 'Address',
                            addr_to: 'Address',
                            func_name: str,
                            arg_params: tuple,
                            kw_params: dict,
                            amount: int) -> Any:
        return self._call(TraceType.CALL, addr_from, addr_to, func_name, arg_params, kw_params, amount)

    def _call(self,
              trace_type: 'TraceType',
              addr_from: 'Address',
              addr_to: 'Address',
              func_name: Optional[str],
              arg_params: tuple,
              kw_params: dict,
              amount: int,
              is_exc_handling: bool = False) -> Any:

        self._make_trace(trace_type, addr_from, addr_to, func_name, arg_params, kw_params, amount)

        if amount > 0 or addr_to.is_contract:
            self.__context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)

        if trace_type == TraceType.CALL:
            ret = self._other_score_call(addr_from, addr_to, func_name, arg_params, kw_params, amount)
        elif trace_type == TraceType.TRANSFER:
            ret = self._icx_transfer(addr_from, addr_to, amount, is_exc_handling)
            if addr_to.is_contract:
                self._other_score_call(addr_from, addr_to, None, (), {}, amount)
        else:
            ret = None
        return ret

    def _make_trace(self,
                    trace_type: 'TraceType',
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
        trace = Trace(_from, trace_type, [_to, func_name, arg_data, amount])
        self.__context.traces.append(trace)

    def _icx_transfer(self, addr_from: 'Address', addr_to: 'Address', icx_value: int, is_exc_handling: bool) -> bool:
        ret = None
        try:
            ret = self.icx_engine.transfer(self.__context, addr_from, addr_to, icx_value)
        except BaseException as e:
            if is_exc_handling:
                pass
            else:
                raise e
        return ret

    def _other_score_call(self,
                          addr_from: Address,
                          addr_to: 'Address',
                          func_name: Optional[str],
                          arg_params: tuple,
                          kw_params: dict,
                          amount: int) -> object:
        """Call the functions provided by other icon scores.

        :param addr_from:
        :param addr_to:
        :param func_name:
        :param arg_params:
        :param kw_params:
        :param amount:
        :return:
        """

        self._validate_score_blacklist(addr_to)
        self.__context.msg_stack.append(self.__context.msg)

        self.__context.msg = Message(sender=addr_from, value=amount)
        self.current_address = addr_to
        icon_score = self.__context.get_icon_score(addr_to)

        if addr_from == icon_score.address:
            raise ServerErrorException("call function myself")

        if func_name is None:
            fallback_func = getattr(icon_score, '_IconScoreBase__fallback_call')
            ret = fallback_func()
        else:
            external_func = getattr(icon_score, '_IconScoreBase__external_call')
            ret = external_func(func_name=func_name, arg_params=arg_params, kw_params=kw_params)

        self.current_address = addr_from
        self.msg = self.__context.msg_stack.pop()

        return ret

    def _validate_score_blacklist(self, address: 'Address'):
        if address == GOVERNANCE_SCORE_ADDRESS:
            return

        governance = self.__context.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
        if governance and governance.isInScoreBlackList(address):
            raise ServerErrorException(f'The Score is in Black List (address: {address})')
