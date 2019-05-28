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

from iconcommons import Logger
from .candidate import Candidate
from ..base.address import Address
from ..base.exception import InvalidParamsException


class Node:
    def __init__(self, data: 'Candidate'):
        Logger.debug(f"Node: {type(data)}, {data}", "iiss")
        self._data: 'Candidate' = data
        self.next: 'Node' = None
        self.prev: 'Node' = None

    @property
    def data(self) -> 'Candidate':
        return self._data


class CandidateLinkedList:
    def __init__(self):
        self._head: 'Node' = None
        self._tail: 'Node' = None
        self._size: int = 0

    def append(self, data: 'Candidate'):
        node = Node(data)
        if self._is_empty():
            self._add_init_node(node)
        else:
            self._append(node)

    def remove(self, address: 'Address'):
        if self._is_empty():
            return

        node: 'Node' = self._get(address)
        if node is None:
            return

        self._remove(node)

    def update(self, address: 'Address', new_delegated: int):
        if self._is_empty():
            return

        update_node: 'Node' = self._get(address)
        if update_node is None:
            raise InvalidParamsException(f"Fail update_sort: node is None")

        self._remove(update_node)
        update_node.data.delegated = new_delegated

        if self._size == 0:
            self._add_init_node(update_node)
        else:
            src_node: 'Node' = None
            it: 'Node' = self._tail
            while it:
                if update_node.data < it.data:
                    src_node = it
                    break
                else:
                    it: 'Node' = it.prev

            if src_node is None:
                # head node
                self._insert_head_node(update_node)
            elif src_node == self._tail:
                # tail node
                self._append(update_node)
            else:
                self._insert_next_to_src_node(src_node, update_node)

    def clear(self):
        self._head = None
        self._tail = None
        self._size = 0

    def _is_empty(self):
        return self._size == 0

    def _add_init_node(self, node: 'Node'):
        assert self._head is None
        assert self._tail is None
        assert self._is_empty()

        self._head = node
        self._tail = node
        self._size += 1

    def _insert_head_node(self, node: 'Node'):
        prev_head = self._head
        prev_head.prev = node
        self._head = node
        self._head.next = prev_head
        self._size += 1

    def _get(self, address: 'Address') -> Optional['Node']:
        node: 'Node' = self._head
        while node:
            if node.data.address == address:
                return node
            else:
                node: 'Node' = node.next
        return None

    def _append(self, node: 'Node'):
        assert self._tail is not None

        prev_tail = self._tail
        self._tail = node
        prev_tail.next = node
        node.prev = prev_tail
        self._size += 1

    def _insert_next_to_src_node(self, src_node: 'Node', node: 'Node'):
        assert src_node is not None
        assert src_node != self._tail

        next_node = src_node.next
        next_node.prev = node

        node.next = next_node
        node.prev = src_node

        src_node.next = node
        self._size += 1

    def _remove(self, node: 'Node'):
        assert not self._is_empty()

        prev_node: 'Node' = node.prev
        next_node: 'Node' = node.next

        node.prev = None
        node.next = None

        if prev_node is None:
            # first node
            self._head = next_node
        else:
            prev_node.next = next_node

        if next_node is None:
            # last node
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
