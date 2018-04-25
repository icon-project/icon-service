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


from threading import Lock

from ..base.address import Address
from ..base.message import Message
from ..base.transaction import Transaction
from ..icx.icx_engine import IcxEngine


class IconScoreContext(object):
    """Provides the current context to IconScore including state, utilities and so on.
    """

    def __init__(self,
                 readonly: bool=False,
                 score_address: Address=None,
                 icx_engine: IcxEngine=None,
                 tx: Transaction=None,
                 msg: Message=None,
                 db=None) -> None:
        """Constructor

        :param readonly: whether state change is possible or not
        :param icx_engine:
        :param tx: initial transaction info
        :param msg: message call info
        """
        self.readonly = readonly
        self.__score_address = score_address
        self.__db = db
        self._icx_engine = icx_engine
        self.tx = tx
        self.msg = msg

    @property
    def db(self):
        return self.__db

    def gasleft(self) -> int:
        """Returns the amount of gas left

        If gasleft is zero before tx handling is complete,
        rollback all changed state for the tx
        Consumed gas doesn't need to be paid back to tx owner.

        :return: the amount of gas left
        """
        return 0

    def get_balance(self, address: Address) -> int:
        """Returns the icx balance of context owner (icon score)

        :return: the icx amount of balance
        """
        return self._icx_engine.get_balance(address)

    def address(self) -> Address:
        """The address of the current icon score

        :return: the address of context owner
        """
        self.__score_address

    def transfer(self, to: Address, amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by 'to'.

        If failed, an exception will be raised.

        :param to: recipient address
        :param amount: icx amount in loop (1 icx == 1e18 loop)
        """
        self._icx_engine._transfer(self.address, to, amount)

    def send(self, to: Address, amount: int) -> bool:
        """Send the amount of icx to the account indicated by 'to'.

        :param to: recipient address
        :param amount: icx amount in loop (1 icx == 1e18 loop)
        :return: True(success), False(failure)
        """
        try:
            return self._icx_engine._transfer(self.address, to, amount)
        except:
            pass

        return False

    def call(self, *args, **kwargs) -> object:
        """Call the functions provided by other icon scores.

        :param args:
        :param kwargs:
        :return:
        """

    def selfdestruct(self, recipient: Address) -> None:
        """Destroy the current icon score, sending its funds to the given address

        :param recipient: fund recipient
        """

    def revert(self, message: str=None) -> None:
        """Abort execution and revert state changes

        :param message: error log message
        """

    def clear(self) -> None:
        pass


class IconScoreContextFactory(object):
    def __init__(self, max_size: int) -> None:
        self._lock = Lock()
        self._queue = []
        self._max_size = max_size

    def create(self) -> IconScoreContext:
        with self._lock:
            if len(self._queue) > 0:
                return self._queue.pop()

        return IconScoreContext()

    def destroy(self, context: IconScoreContext) -> None:
        with self._lock:
            if len(self._queue) < self._max_size:
                context.clear()
                self._queue.append(context)
