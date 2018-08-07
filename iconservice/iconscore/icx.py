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
from .icon_score_step import StepType
from .icon_score_trace import Trace, TraceType

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from ..base.address import Address


class Icx(object):
    """Class for handling ICX coin transfer
    """

    def __init__(self, context: 'IconScoreContext', address: 'Address') -> None:
        """Constructor
        """
        self._context = context
        self._address = address

    def transfer(self, addr_to: 'Address', amount: int) -> bool:
        return self._context.internal_call(TraceType.TRANSFER, self._address, addr_to, None, [], {}, amount)

    def send(self, addr_to: 'Address', amount: int) -> bool:
        return self._context.internal_call(TraceType.TRANSFER, self._address, addr_to, None, [], {}, amount, True)

    def get_balance(self, address: 'Address') -> int:
        return self._context.get_balance(address)
