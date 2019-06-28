# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
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

from abc import ABCMeta, abstractmethod
from typing import Union, Iterable, List, Optional


class Sortable(metaclass=ABCMeta):
    @abstractmethod
    def order(self):
        pass


class SortedList(object):
    def __init__(self, sorted_list: 'SortedList' = ()):
        self._items = list(sorted_list)

    def add(self, new_item: 'Sortable'):
        """

        :param new_item:
        :return:
        """
        index = 0
        order = new_item.order()

        for item in self._items:
            if order < item.order():
                break

            index += 1

        self._items.insert(index, new_item)

    def get(self, index: int) -> Optional['Sortable']:
        try:
            return self._items[index]
        except IndexError:
            return None

    def extend(self, iterable: Iterable['Sortable']):
        self._items.extend(iterable)

    def reorder(self, item: 'Sortable'):
        self._items.remove(item)
        self.add(item)

    def index(self, item: 'Sortable') -> int:
        order = item.order()

        left: int = 0
        right: int = len(self._items)

        while left < right:
            i = (left + right) // 2
            item_in_list: 'Sortable' = self._items[i]

            if order == item_in_list.order():
                return i

            if order < item_in_list.order():
                right = i
            else:
                left = i + 1

        return -1

    def remove(self, item: 'Sortable') -> 'Sortable':
        index: int = self.index(item)
        if index > -1:
            return self.pop(index)

        raise ValueError(f"Value not found")

    def pop(self, index: int) -> 'Sortable':
        return self._items.pop(index)

    def append(self, item: 'Sortable'):
        self._items.append(item)

    def __iter__(self):
        for item in self._items:
            yield item

    def __getitem__(self, k: Union[int, slice]) -> Union['Sortable', List['Sortable']]:
        if isinstance(k, slice):
            return self._items[k]
        return self._items[k]

    def __setitem__(self, index: int, value: 'Sortable'):
        self._items[index] = value

    def __len__(self) -> int:
        return len(self._items)
