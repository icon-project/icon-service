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

from typing import TYPE_CHECKING

from .icon_score_constant import STR_FALLBACK
from .icon_score_context_util import IconScoreContextUtil
from .internal_call import InternalCall
from ..base.address import GOVERNANCE_SCORE_ADDRESS

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from ..base.address import Address


class Icx(object):
    """Class for handling ICX coin transfer

    These functions are intended to be used for SCORE development.
    """

    def __init__(self, context: 'IconScoreContext', address: 'Address') -> None:
        """Constructor
        """
        self._context = context
        self._address = address

    def transfer(self, addr_to: 'Address', amount: int) -> None:
        """
        transfer the amount of icx to the given 'addr_to'
        If failed, an exception will be raised

        :param addr_to: receiver address
        :param amount: the amount of icx to transfer (unit: loop)
        """
        InternalCall.other_external_call(self._context, self._address, addr_to, amount, STR_FALLBACK)

    def send(self, addr_to: 'Address', amount: int) -> bool:
        """
        transfer the amount of icx to the given 'addr_to'

        :param addr_to: receiver address
        :param amount: the amount of icx to transfer (unit: loop)
        :return: True(success) False(failed)
        """
        try:
            self.transfer(addr_to, amount)
            if not addr_to.is_contract and self._is_icx_send_defective():
                return False
            return True
        except:
            return False

    def get_balance(self, address: 'Address') -> int:
        """
        Returns the ICX balance of given address

        :param address: address
        :return: ICX balance of given address
        """
        return InternalCall.icx_get_balance(self._context, address)

    # noinspection PyBroadException
    def _is_icx_send_defective(self) -> bool:
        try:
            governance_score = IconScoreContextUtil.get_builtin_score(
                self._context, GOVERNANCE_SCORE_ADDRESS)

            if hasattr(governance_score, 'getVersion'):
                version = governance_score.getVersion()
                return version == '0.0.2'
        except BaseException:
            pass

        return False
