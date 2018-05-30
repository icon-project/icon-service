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


import abc
import json
from typing import List

from iconservice.utils import to_camel_case

from ..base.address import Address
from ..base.block import Block


class TransactionResult(object):
    """ A DataClass of a transaction result.
    """

    SUCCESS = 1
    FAILURE = 0

    def __init__(
            self,
            tx_hash: str,
            block: Block,
            to: Address,
            status: int = FAILURE,
            contract_address: Address = None,
            step_used: int = 0) -> None:
        """Constructor

        :param tx_hash: transaction hash
        :param block: a block that the transaction belongs to
        :param to: a recipient address
        :param step_used: the amount of steps used in the transaction
        :param contract_address:hex string that represent the contract address
            if the transaction`s target is contract
        :param status: a status of result. 1 (success) or 0 (failure)
        """
        self.tx_hash = tx_hash
        self.block = block
        self.to = to
        self.contract_address = contract_address
        self.step_used = step_used
        self.status = status

    def __str__(self) -> str:
        return \
            f'status: {self.status}\n' \
            f'tx_hash: {self.tx_hash}\n' \
            f'to: {self.to}\n' \
            f'contract_address: {self.contract_address}\n' \
            f'step_used: {self.step_used}'

    def to_dict(self) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Block):
                new_dict["block_height"] = value.height
            elif isinstance(value, Address):
                new_dict[key] = str(value)
            else:
                new_dict[key] = value

        return new_dict

    def to_response_json(self) -> dict:
        """
        Returns properties as json-rpc-v3 json
        :return: a dict
        """
        response_json = {}
        tx_dict = self.to_dict()
        for key, value in tx_dict.items():
            key = to_camel_case(key)
            response_json[key] = value
        return response_json


class Serializer(abc.ABC):
    """ An abstract class serialize results of transactions.
    """

    @abc.abstractmethod
    def serialize(self, transaction_results: List[TransactionResult]) -> bytes:
        """Returns a serialized data of the results of transactions.

        :return: a serialized data.
        """
        pass


class IconBlockResult(list):
    """ The class manage results of transactions.
    """

    def __init__(self, serializer: Serializer) -> None:
        """Constructor

        :param serializer: serializer
        """
        super().__init__()
        self.__serializer = serializer

    def serialize(self) -> bytes:
        """Returns a serialized data of the block result.

        :return: a serialized data.
        """
        return self.__serializer.serialize(self)


class JsonSerializer(Serializer):
    def serialize(self, transaction_results: List[TransactionResult]) -> bytes:
        """Returns a serialized data of the results of transactions.

        :return: a serialized data.
        """
        serialized = json.dumps(transaction_results, cls=JsonSerializer.Encoder)
        return bytes(serialized, 'utf-8')

    class Encoder(json.JSONEncoder):
        """Converter class
        """

        def default(self, obj):
            if isinstance(obj, TransactionResult):
                return obj.to_dict()

            return super().default(obj)
