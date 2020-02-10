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
from typing import TYPE_CHECKING, Optional, List, Tuple

from ..base.exception import FatalException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address

_TAG = "PRepKeyConverter"


class PRepKeyConverter:
    """
    Convert prep address being used for consensus in loopchain (i.e. node key) to
    P-Rep address being used for managing P-Rep (i.e. operation key).

    Loopchain distinguish P-Reps using node key, but iconservice uses an operation key as a identification.
    """

    def __init__(self,
                 prev_node_key_mapper: dict = None,
                 node_key_mapper: dict = None):
        # For P-Rep vote reward
        if prev_node_key_mapper:
            self._prev_node_key_mapper: dict = prev_node_key_mapper
        else:
            self._prev_node_key_mapper: dict = {}

        # For assign node key validating
        if node_key_mapper:
            self._node_key_mapper: dict = node_key_mapper
        else:
            self._node_key_mapper: dict = {}

    def load(self, context: 'IconScoreContext'):
        self._prev_node_key_mapper: dict = context.storage.meta.get_prev_node_key_mapper(context)

    def save(self, context: 'IconScoreContext'):
        context.storage.meta.put_prev_node_key_mapper(context, context.prep_key_converter.prev_node_key_mapper)

    @property
    def prev_node_key_mapper(self) -> dict:
        return self._prev_node_key_mapper

    @property
    def node_key_mapper(self) -> dict:
        return self._node_key_mapper

    def add_node_key_mapper(self, key: 'Address', value: 'Address'):
        self._node_key_mapper[key] = value

    def add_prev_node_key_mapper(self, key: 'Address', value: 'Address'):
        self._prev_node_key_mapper[key] = value

    def delete_node_key_mapper(self, key: 'Address'):
        del self._node_key_mapper[key]

    def copy(self) -> 'PRepKeyConverter':
        return PRepKeyConverter(prev_node_key_mapper=copy.copy(self.prev_node_key_mapper),
                                node_key_mapper=copy.copy(self.node_key_mapper))

    def node_key_to_operation_key(self,
                                  prev_block_generator: Optional['Address'] = None,
                                  prev_block_votes: Optional[List[Tuple['Address', int]]] = None) -> tuple:

        prev_block_generator: 'Address' = self._get_operation_key_from_node_key(prev_block_generator)
        tmp_votes: List[Tuple['Address', int]] = []

        for address, vote in prev_block_votes:
            if self._is_contains_node_key_mapper(address):
                tmp_votes.append([self._get_operation_key_from_node_key(address), vote])
            else:
                tmp_votes.append([address, vote])
        prev_block_votes: List[Tuple['Address', int]] = tmp_votes
        return prev_block_votes, prev_block_generator

    def reset_prev_node_key_mapper(self):
        self._prev_node_key_mapper.clear()

    def _is_contains_node_key_mapper(self,
                                     node_key: 'Address') -> bool:
        ret: bool = node_key in self._prev_node_key_mapper
        if not ret:
            ret: bool = node_key in self._node_key_mapper
        return ret

    def _get_operation_key_from_node_key(self,
                                         node_key: 'Address') -> 'Address':
        address: Optional['Address'] = self._prev_node_key_mapper.get(node_key)
        if address is None:
            address: 'Address' = self._node_key_mapper.get(node_key)

        if address is None:
            address: 'Address' = node_key

        if address is None:
            raise FatalException(f"Invalid node key {address}")
        return address
