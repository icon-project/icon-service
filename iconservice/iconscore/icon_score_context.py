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
from ..base.exception import IconScoreBaseException, PayableException, ExternalException
from ..icx.icx_engine import IcxEngine
from .icon_score_info_mapper import IconScoreInfoMapper, IconScoreInfo
from ..database.batch import BlockBatch, TransactionBatch


class IconScoreContext(object):
    """Provides the current context to IconScore including state, utilities and so on.
    """
    icx: IcxEngine = None
    score_mapper: IconScoreInfoMapper = None

    def __init__(self,
                 readonly: bool = True,
                 tx: Transaction = None,
                 msg: Message = None,
                 block_batch: BlockBatch = None,
                 tx_batch: TransactionBatch = None) -> None:
        """Constructor

        :param readonly: whether state change is possible or not
        :param icx:
        :param tx: initial transaction info
        :param msg: message call info
        """
        self.readonly = readonly
        self.tx = tx
        self.msg = msg
        self.block_batch = None
        self.tx_batch = None

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
        return self.icx.get_balance(address)

    def transfer(self, addr_from: Address, addr_to: Address, amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by 'to'.

        If failed, an exception will be raised.

        :param addr_from:
        :param addr_to:
        :param amount: icx amount in loop (1 icx == 1e18 loop)
        """
        return self.icx.transfer(addr_from, addr_to, amount)

    def send(self, addr_from: Address, addr_to: Address, amount: int) -> bool:
        """Send the amount of icx to the account indicated by 'to'.

        :param addr_from:
        :param addr_to: recipient address
        :param amount: icx amount in loop (1 icx == 1e18 loop)
        :return: True(success), False(failure)
        """
        try:
            return self.icx.transfer(addr_from, addr_to, amount)
        except:
            pass

        return False

    def call(self, addr_from: Address, addr_to: Address, func_name: str, *args, **kwargs) -> None:
        """Call the functions provided by other icon scores.

        :param addr_from:
        :param addr_to:
        :param func_name:
        :param args:
        :param kwargs:
        :return:
        """

        call_method(addr_from=addr_from, addr_to=addr_to, score_mapper=self.__score_mapper,
                    readonly=self.readonly, func_name=func_name, *args, **kwargs)

    def selfdestruct(self, recipient: Address) -> None:
        """Destroy the current icon score, sending its funds to the given address

        :param recipient: fund recipient
        """

    def revert(self, message: str = None) -> None:
        """Abort execution and revert state changes

        :param message: error log message
        """

    def clear(self) -> None:
        """Set instance member variables to None
        """
        self.tx = None
        self.msg = None
        self.block_batch = None
        self.tx_batch = None


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


def call_method(addr_to: Address, score_mapper: IconScoreInfoMapper,
                readonly: bool, func_name: str, addr_from: object=None, *args, **kwargs) -> object:

    icon_score_info = __get_icon_score_info(addr_from, addr_to, score_mapper)
    icon_score = icon_score_info.get_icon_score(readonly)

    try:
        return icon_score.call_method(func_name, *args, **kwargs)
    except (PayableException, ExternalException):
        call_fallback(addr_to=addr_to,
                      score_mapper=score_mapper,
                      readonly=readonly,
                      addr_from=addr_from)
        return None


def call_fallback(addr_to: Address, score_mapper: IconScoreInfoMapper,
                  readonly: bool, addr_from: object=None) -> None:

    icon_score_info = __get_icon_score_info(addr_from, addr_to, score_mapper)
    icon_score = icon_score_info.get_icon_score(readonly)
    icon_score.call_fallback()


def __get_icon_score_info(addr_from: object, addr_to: Address, score_mapper: IconScoreInfoMapper) -> IconScoreInfo:
    if addr_from == addr_to:
        raise IconScoreBaseException("call function myself")

    icon_score_info = score_mapper.get(addr_to)
    if icon_score_info is None:
        raise IconScoreBaseException("icon_score_info is None")

    return icon_score_info
