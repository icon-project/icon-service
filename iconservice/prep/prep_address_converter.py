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

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address

_TAG = "PRepAddressConverter"


class PRepAddressConverter:
    """
    Convert prep address being used for consensus in loopchain (i.e. node address) to
    P-Rep address being used for managing P-Rep (i.e. prep address).

    Loopchain distinguish P-Reps using node address, but iconservice uses an prep address as a identification.
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

    def load(self, context: 'IconScoreContext'):
        self._prev_node_address_mapper: dict = context.storage.meta.get_prev_node_address_mapper(context)

    def save(self, context: 'IconScoreContext'):
        context.storage.meta.put_prev_node_address_mapper(context,
                                                          self._prev_node_address_mapper)

    @property
    def prev_node_address_mapper(self) -> dict:
        return self._prev_node_address_mapper

    @property
    def node_address_mapper(self) -> dict:
        return self._node_address_mapper

    def add_node_address_mapper(self, key: 'Address', value: 'Address'):
        self._node_address_mapper[key] = value

    def add_prev_node_address_mapper(self, key: 'Address', value: 'Address'):
        if value not in self._prev_node_address_mapper:
            self._prev_node_address_mapper[key] = value

    def delete_node_address_mapper(self, key: 'Address'):
        if key in self._node_address_mapper:
            del self._node_address_mapper[key]

    def copy(self) -> 'PRepAddressConverter':
        return PRepAddressConverter(prev_node_address_mapper=copy.copy(self.prev_node_address_mapper),
                                    node_address_mapper=copy.copy(self.node_address_mapper))

    def node_address_to_prep_address(self,
                                     prev_block_generator: Optional['Address'] = None,
                                     prev_block_votes: Optional[List[Tuple['Address', int]]] = None) -> tuple:

        prev_block_generator: 'Address' = self._get_prep_address_from_node_address(prev_block_generator)
        tmp_votes: List[Tuple['Address', int]] = []

        for address, vote in prev_block_votes:
            if self._is_contains_node_address(address):
                tmp_votes.append([self._get_prep_address_from_node_address(address), vote])
            else:
                tmp_votes.append([address, vote])
        prev_block_votes: List[Tuple['Address', int]] = tmp_votes
        return prev_block_votes, prev_block_generator

    def reset_prev_node_address(self):
        self._prev_node_address_mapper.clear()

    def _is_contains_node_address(self,
                                         node_address: 'Address') -> bool:
        return node_address in self._prev_node_address_mapper or node_address in self._node_address_mapper

    def _get_prep_address_from_node_address(self,
                                            node_address: 'Address') -> 'Address':
        return self._prev_node_address_mapper.get(node_address,
                                                  self._node_address_mapper.get(node_address, node_address))
