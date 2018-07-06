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
from typing import TYPE_CHECKING, List, Optional

from iconservice.utils.bloom import BloomFilter
from ..utils import to_camel_case
from ..base.address import Address
from ..base.block import Block
from .icon_score_event_log import EventLog

if TYPE_CHECKING:
    pass


class TransactionResult(object):
    """ A DataClass of a transaction result.
    """

    SUCCESS = 1
    FAILURE = 0

    class Failure(object):
        def __init__(self, code: int, message: str):
            self.code = int(code)
            self.message = str(message)

    def __init__(
            self,
            tx_hash: bytes,
            block: 'Block',
            tx_index: int,
            to: Optional['Address'] = None,
            status: int = FAILURE,
            score_address: Optional['Address'] = None,
            event_logs: Optional[List['EventLog']] = None,
            logs_bloom: Optional[BloomFilter] = None,
            step_used: int = FAILURE) -> None:
        """Constructor

        :param tx_hash: transaction hash
        :param block: a block that the transaction belongs to
        :param tx_index: an index of a transaction on the block
        :param to: a recipient address
        :param score_address:hex string that represent the contract address
            if the transaction`s target is contract
        :param step_used: the amount of steps used in the transaction
        :param event_logs: the amount of steps used in the transaction
        :param logs_bloom: bloom filter data of event logs
        :param status: a status of result. 1 (success) or 0 (failure)
        """
        self.tx_hash = tx_hash
        self.block = block
        self.tx_index = tx_index
        self.to = to
        self.score_address = score_address
        self.step_used = step_used
        self.event_logs = event_logs
        self.logs_bloom = logs_bloom
        self.status = status

        # failure object which has code(int) and message(str) attributes
        # It is only available on self.status == FAILURE
        self.failure = None

        # Traces are managed in TransactionResult but not passed to chain engine
        self.traces = None

    def __str__(self) -> str:
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])

    def to_dict(self, casing: Optional = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Block):
                key = "block_height"
                value = value.height
            elif key == 'event_logs' and value:
                value = [v.to_dict(casing) for v in value
                         if isinstance(v, EventLog)]
            elif isinstance(value, BloomFilter):
                value = int(value).to_bytes(256, byteorder='big')
            elif key == 'failure' and value:
                if self.status == self.FAILURE:
                    value = {
                        'code': value.code,
                        'message': value.message
                    }
                else:
                    value = None
            elif key == 'traces':
                # traces are excluded from dict property
                continue

            # Excludes properties which have `None` value
            if value is not None:
                new_dict[casing(key) if casing else key] = value

        return new_dict
