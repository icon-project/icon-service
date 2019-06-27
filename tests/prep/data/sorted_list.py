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

import random

import pytest

from iconservice.prep.data.sorted_list import SortedList, Sortable


class SortedItem(Sortable):
    def __init__(self, value: int):
        self.value = value

    def order(self):
        return self.value


def check_sorted_list(items: 'SortedList'):
    prev_item = None

    for item in items:
        assert isinstance(item, Sortable)
        if prev_item:
            assert prev_item.order() <= item.order()


@pytest.fixture
def create_sorted_list():
    def _create_sorted_list(size: int):
        items = SortedList()

        for i in range(size):
            item = SortedItem(random.randint(-10000, 10000))
            items.add(item)

        assert len(items) == size
        return items

    return _create_sorted_list


def test_add(create_sorted_list):
    size = 100
    items = create_sorted_list(size)
    check_sorted_list(items)

    item = SortedItem(random.randint(-9999, 9999))
    items.add(item)
    assert len(items) == size + 1
    check_sorted_list(items)


def test_remove(create_sorted_list):
    for size in (1, 99, 100):
        items = create_sorted_list(size)
        assert len(items) == size

        index: int = random.randint(0, size - 1)
        item = items[index]
        assert item is not None
        removed_item = items.remove(item)
        assert item == removed_item
        assert len(items) == size - 1
        check_sorted_list(items)

    item = SortedItem(0)
    items = SortedList()
    assert len(items) == 0

    with pytest.raises(ValueError):
        removed_item = items.remove(item)


def test_pop(create_sorted_list):
    for size in (1, 99, 100):
        items = create_sorted_list(size)
        assert len(items) == size

        index: int = random.randint(0, size - 1)
        item = items[index]

        popped_item = items.pop(index)
        assert item == popped_item
        assert len(items) == size - 1
        check_sorted_list(items)

    items = SortedList()
    assert len(items) == 0

    with pytest.raises(IndexError):
        items.pop(0)


def test_index(create_sorted_list):
    for size in (1, 2, 99, 100):
        items = create_sorted_list(size)
        assert len(items) == size

        indexes = set()
        indexes.add(0)
        indexes.add(max(0, size - 1))
        if size - 2 > 1:
            indexes.add(random.randint(1, size - 2))

        for index in indexes:
            i = items.index(items[index])
            assert i == index
