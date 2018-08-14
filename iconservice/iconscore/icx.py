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
        return self._context.internal_call.icx_transfer_call(self._address, addr_to, amount)

    def send(self, addr_to: 'Address', amount: int) -> bool:
        return self._context.internal_call.icx_send_call(self._address, addr_to, amount)

    def get_balance(self, address: 'Address') -> int:
        return self._context.internal_call.get_icx_balance(address)
