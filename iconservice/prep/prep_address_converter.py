# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from typing import TYPE_CHECKING

from ..base.exception import InvalidParamsException
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address

_TAG = "PRepAddressConverter"


class PRepAddressConverter:
    """
    Convert prep address being used for consensus in loopchain (i.e. node address) to
    P-Rep address being used for managing P-Rep (i.e. prep address).

    Loopchain distinguishes P-Reps using node address, but iconservice uses an prep address as a identification.
    """

    def __init__(self,
                 prev_node_address_mapper: dict = None,
                 node_address_mapper: dict = None):
        # For P-Rep vote reward
        if prev_node_address_mapper:
            self._prev_node_address_mapper: dict = prev_node_address_mapper
        else:
            self._prev_node_address_mapper: dict = {}

        # For assign node address validating
        if node_address_mapper:
            self._node_address_mapper: dict = node_address_mapper
        else:
            self._node_address_mapper: dict = {}

    def __str__(self):
        return f"prev_node_address_mapper={self._prev_node_address_mapper} \n" \
               f"node_address_mapper={self._node_address_mapper}"

    def to_bytes(self) -> bytes:
        version: int = 0
        return MsgPackForDB.dumps([version, self._prev_node_address_mapper])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PRepAddressConverter':
        if data is None:
            return PRepAddressConverter()

        data: list = MsgPackForDB.loads(data)
        _version = data[0]

        prev_node_address_mapper: dict = data[1]
        return PRepAddressConverter(prev_node_address_mapper=prev_node_address_mapper)

    def add_node_address(self, node: 'Address', prep: 'Address'):
        if node in self._node_address_mapper:
            raise InvalidParamsException(f"nodeAddress already in use: {node}")
        self._node_address_mapper[node] = prep

    def delete_node_address(self, node: 'Address', prep: 'Address'):
        self._add_prev_node_address(node=node, prep=prep)
        self._delete_node_address(node)

    def _delete_node_address(self, node: 'Address'):
        if node in self._node_address_mapper:
            del self._node_address_mapper[node]

    def _add_prev_node_address(self, node: 'Address', prep: 'Address'):
        if prep not in self._prev_node_address_mapper.values():
            self._prev_node_address_mapper[node] = prep

    def replace_node_address(self, node: 'Address', prep: 'Address', prev_node: 'Address'):
        self._add_prev_node_address(node=prev_node, prep=prep)
        self._delete_node_address(node=prev_node)
        self.add_node_address(node=node, prep=prep)

    def copy(self) -> 'PRepAddressConverter':
        return PRepAddressConverter(prev_node_address_mapper=copy.copy(self._prev_node_address_mapper),
                                    node_address_mapper=copy.copy(self._node_address_mapper))

    def reset_prev_node_address(self):
        self._prev_node_address_mapper.clear()

    def validate_node_address(self,
                              node: 'Address'):

        if node in self._node_address_mapper:
            raise InvalidParamsException(f"nodeAddress already in use: {node}")

    def get_prep_address_from_node_address(self,
                                           node_address: 'Address') -> 'Address':
        ret: 'Address' = self._node_address_mapper.get(node_address)
        if ret is None:
            ret = self._prev_node_address_mapper.get(node_address, node_address)
        return ret
