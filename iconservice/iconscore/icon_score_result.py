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

from typing import TYPE_CHECKING, List, Optional

from .icon_score_event_log import EventLog
from ..base.address import Address
from ..base.block import Block
from ..base.exception import ExceptionCode
from ..icon_constant import DATA_BYTE_ORDER
from ..utils import bytes_to_hex
from ..utils.bloom import BloomFilter

if TYPE_CHECKING:
    from ..base.transaction import Transaction


class TransactionResult(object):
    """ A DataClass of a transaction result.
    """

    SUCCESS = 1
    FAILURE = 0

    class Failure(object):
        def __init__(self, code: int, message: str):
            """MUST check arguments type strictly

            :param code: error code
            :param message: error message
            """
            if type(code) != int:
                code = ExceptionCode.SYSTEM_ERROR.value
            if type(message) != str:
                message = 'Invalid argument: message is not a string'

            self.code = code
            self.message = message

    def __init__(
            self,
            tx: 'Transaction',
            block: 'Block',
            to: Optional['Address'] = None,
            score_address: Optional['Address'] = None,
            step_used: int = 0,
            step_price: int = 0,
            cumulative_step_used: int = 0,
            event_logs: Optional[List['EventLog']] = None,
            logs_bloom: Optional[BloomFilter] = None,
            status: int = FAILURE) -> None:
        """Constructor

        :param tx: transaction
        :param block: a block that the transaction belongs to
        :param to: a recipient address
        :param score_address:hex string that represent the contract address
            if the transaction`s target is contract
        :param step_used: the amount of steps used in the transaction
        :param event_logs: the amount of steps used in the transaction
        :param logs_bloom: bloom filter data of event logs
        :param status: a status of result. 1 (success) or 0 (failure)
        """
        self.tx_hash = tx.hash
        self.block_height = block.height
        self.block_hash = block.hash
        self.tx_index = tx.index
        self.to = to
        self.score_address = score_address
        self.step_used = step_used
        self.step_price = step_price
        self.cumulative_step_used = cumulative_step_used
        self.event_logs = event_logs
        self.logs_bloom = logs_bloom
        self.status = status

        # Details of the used step. This is set if the SCORE pays fees.
        # Otherwise left as `None` and not passed to transaction result.
        self.step_used_details: Optional[dict] = None

        # failure object which has code(int) and message(str) attributes
        # It is only available on self.status == FAILURE
        self.failure = None

        # Traces are managed in TransactionResult but not passed to chain engine
        self.traces = None

    def __str__(self) -> str:
        def func():
            for k, v in self.__dict__.items():
                if isinstance(v, bytes):
                    v = bytes_to_hex(v)
                yield f'{k}: {v}'

        return '\n'.join(func())

    def to_dict(self, casing: Optional[callable] = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            # Excludes properties which have `None` value
            if value is None:
                continue

            new_key = casing(key) if casing else key
            if key == 'event_logs':
                new_dict[new_key] = [v.to_dict(casing) for v in value if
                                     isinstance(v, EventLog)]
            elif isinstance(value, BloomFilter):
                new_dict[new_key] = int(value).to_bytes(256, byteorder=DATA_BYTE_ORDER)
            elif key == 'failure':
                if self.status == self.FAILURE:
                    new_dict[new_key] = {
                        'code': value.code,
                        'message': value.message
                    }
            elif key == 'step_used_details':
                assert isinstance(value, dict)
                step_used_details = {}
                new_dict[new_key] = step_used_details

                for address in value:
                    step_used_details[str(address)] = value[address]
            elif key == 'traces':
                # traces are excluded from dict property
                continue
            else:
                new_dict[new_key] = value

        return new_dict
