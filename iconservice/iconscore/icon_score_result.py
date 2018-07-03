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


from ..utils import to_camel_case
from ..base.address import Address
from ..base.block import Block

from typing import Optional


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
            step_used: int = 0) -> None:
        """Constructor

        :param tx_hash: transaction hash
        :param block: a block that the transaction belongs to
        :param tx_index: an index of a transaction on the block
        :param to: a recipient address
        :param step_used: the amount of steps used in the transaction
        :param score_address:hex string that represent the contract address
            if the transaction`s target is contract
        :param status: a status of result. 1 (success) or 0 (failure)
        """
        self.tx_hash = tx_hash
        self.block = block
        self.tx_index = tx_index
        self.to = to
        self.score_address = score_address
        self.step_used = step_used
        self.status = status

        # failure object which has code(int) and message(str) attributes
        # It is only available on self.status == FAILURE
        self.failure = None

    def __str__(self) -> str:
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])

    def _to_dict(self) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                # Excludes properties which have `None` value
                continue

            if isinstance(value, Block):
                new_dict["block_height"] = value.height
            elif isinstance(value, Address):
                new_dict[key] = str(value)
            elif isinstance(value, bytes):
                new_dict[key] = bytes.hex(value)
            elif key == 'failure' and value:
                if self.status == self.FAILURE:
                    new_dict[key] = {
                        'code': value.code,
                        'message': value.message
                    }
            else:
                new_dict[key] = value

        return new_dict

    def to_response_json(self) -> dict:
        """
        Returns properties as json-rpc-v3 json
        :return: a dict
        """
        response_json = {}
        tx_dict = self._to_dict()
        for key, value in tx_dict.items():
            key = to_camel_case(key)
            response_json[key] = value
        return response_json
