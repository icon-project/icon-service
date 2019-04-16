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

from typing import Optional

from ..base.exception import InvalidParamsException
from ..base.address import Address
from .prep_candidate_info_for_sort import PRepCandidateInfoForSort


class Node:
    def __init__(self, data: 'PRepCandidateInfoForSort'):
        self._data: 'PRepCandidateInfoForSort' = data
        self.next: 'Node' = None
        self.prev: 'Node' = None

    @property
    def data(self) -> 'PRepCandidateInfoForSort':
        return self._data


class PRepCandidateLinkedList:
    def __init__(self):
        self._head: 'Node' = None
        self._tail: 'Node' = None
        self._size: int = 0

    def append(self, data: 'PRepCandidateInfoForSort'):
        new_node = Node(data)
        self._append(new_node)

    def remove(self, address: 'Address'):
        node: 'Node' = self._find_by_address(address)
        if node is None:
            return
        self._remove_node(node)

    def _find_by_address(self, address: 'Address') -> Optional['Node']:
        if self._head is None:
            return None

        node: 'Node' = self._head
        while node:
            if node.data.address == address:
                return node
            else:
                node: 'Node' = node.next
        return None

    def update(self, address: 'Address', new_total_delegated: int):
        update_node: 'Node' = self._find_by_address(address)
        if update_node is None:
            raise InvalidParamsException(f"Fail update_sort: node is None")

        update_node.data.update(new_total_delegated)
        self._remove_node(update_node)

        node: 'Node' = None
        it: 'Node' = self._tail
        while it:
            if update_node.data < it.data:
                node = it
                break
            else:
                it: 'Node' = it.prev

        self._insert_next_src_node(node, update_node)

    def _append(self, new_node: 'Node'):
        if self._tail is None:
            self._head = new_node
            self._tail = new_node
        else:
            prev_tail = self._tail
            self._tail = new_node
            prev_tail.next = new_node
            new_node.prev = prev_tail
        self._size += 1

    def _insert_next_src_node(self, src_node: 'Node', new_node: 'Node'):
        if src_node is None:
            prev_head = self._head
            self._head = new_node
            prev_head.prev = new_node
            new_node.next = prev_head
            self._head = new_node
        elif src_node.next is None:
            self._tail = new_node
            src_node.next = new_node
            new_node.prev = src_node
        else:
            new_node.next = src_node.next
            new_node.prev = src_node
            src_node.next = new_node

        self._size += 1

    def _remove_node(self, node: 'Node'):

        prev_node: 'Node' = node.prev
        node.prev = None
        next_node: 'Node' = node.next
        node.next = None

        if prev_node is None:
            self._head = next_node
        else:
            prev_node.next = next_node

        if next_node is None:
            self._tail = prev_node
        else:
            next_node.prev = prev_node
        self._size -= 1

    def __iter__(self):
        return self._get_generator()

    def _get_generator(self):
        n: 'Node' = self._head
        while n:
            yield n
            n = n.next
