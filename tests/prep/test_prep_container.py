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

import os
import random
from typing import Set, Optional

# noinspection PyPackageRequirements
import pytest
from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import AccessDeniedException, InvalidParamsException
from iconservice.prep.data import PRep, PRepContainer, PRepStatus


def _create_dummy_prep(index: int, status: 'PRepStatus' = PRepStatus.ACTIVE) -> 'PRep':
    address = Address(AddressPrefix.EOA, os.urandom(20))

    return PRep(
        address=address,
        status=status,
        name=f"node{index}",
        country="KOR",
        city="Seoul",
        email=f"node{index}@example.com",
        website=f"https://node{index}.example.com",
        details=f"https://node{index}.example.com/details",
        p2p_endpoint=f"node{index}.example.com:7100",
        delegated=random.randint(0, 1000),
        irep=10_000,
        irep_block_height=index,
        block_height=index
    )


@pytest.fixture
def create_prep_container() -> callable:
    def _create_prep_container(size: int = 100) -> 'PRepContainer':
        preps = PRepContainer()

        for i in range(size):
            prep = _create_dummy_prep(i)
            preps.add(prep)

        assert preps.size(active_prep_only=True) == size
        assert preps.size(active_prep_only=False) == size
        return preps

    return _create_prep_container


def test_getitem(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    for i in range(size):
        prep_by_index: 'PRep' = preps.get_by_index(i)
        prep_by_address: 'PRep' = preps.get_by_address(prep_by_index.address)
        assert prep_by_index == prep_by_address
        assert id(prep_by_index) == id(prep_by_address)


def test_get_by_address(create_prep_container):
    size = 10
    preps = create_prep_container(size)

    index: int = random.randint(0, size - 1)
    prep: 'PRep' = preps.get_by_index(index)
    assert isinstance(prep, PRep)

    indexed_prep: 'PRep' = preps.get_by_address(prep.address)
    assert id(prep) == id(indexed_prep)

    removed_prep: 'PRep' = preps.remove(prep.address)
    assert id(prep) == id(removed_prep)

    returned_prep: 'PRep' = preps.get_by_address(prep.address)
    assert returned_prep is None

    prep: 'PRep' = _create_dummy_prep(10, PRepStatus.UNREGISTERED)
    preps.add(prep)
    assert preps.size(active_prep_only=False) == 10
    assert preps.size(active_prep_only=True) == 9

    returned_prep = preps.get_by_address(prep.address)
    assert id(prep) == id(returned_prep)


def test_get_by_index(create_prep_container):
    size = 10
    preps = create_prep_container(size)

    old_preps: Set['PRep'] = set()

    # Index
    for i in range(size):
        prep: 'PRep' = preps.get_by_index(i)
        assert prep is not None
        assert preps not in old_preps
        old_preps.add(prep)

    prep = preps.get_by_index(size)
    assert prep is None

    # Reverse index
    for i in range(1, size + 1):
        prep = preps.get_by_index(-i)
        assert prep is not None
        assert prep == preps.get_by_index(size - i)


def test_index(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    for _ in range(10):
        i = random.randint(0, size - 1)
        prep = preps.get_by_index(i)

        index: int = preps.index(prep.address)
        assert 0 <= index < size
        assert id(prep) == id(preps.get_by_index(index))


def test_freeze(create_prep_container):
    size: int = 100
    preps: 'PRepContainer' = create_prep_container(size)

    preps.freeze()

    i = random.randint(0, size - 1)
    prep = preps.get_by_index(i)

    with pytest.raises(AccessDeniedException):
        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        preps.add(PRep(address))

    with pytest.raises(AccessDeniedException):
        preps.remove(prep.address)


def test_total_delegated(create_prep_container):
    size: int = 51
    preps: 'PRepContainer' = create_prep_container(size)

    total_delegated: int = 0
    for prep in preps:
        total_delegated += prep.delegated

    assert total_delegated == preps.total_delegated

    # Case: remove a P-Rep
    for _ in range(size // 2):
        active_prep_count: int = preps.size(active_prep_only=True)
        index: int = random.randint(0, active_prep_count - 1)
        prep: 'PRep' = preps.get_by_index(index)
        assert prep.status == PRepStatus.ACTIVE

        expected_total_delegated: int = preps.total_delegated - prep.delegated
        removed_prep = preps.remove(prep.address)
        assert id(prep) == id(removed_prep)
        assert preps.total_delegated == expected_total_delegated

    # Case: add a P-Rep
    size = preps.size(active_prep_only=True)
    for _ in range(size // 2):
        size: int = preps.size(active_prep_only=True)
        index = size

        new_prep: 'PRep' = _create_dummy_prep(index)
        assert new_prep.status == PRepStatus.ACTIVE

        expected_total_delegated: int = preps.total_delegated + new_prep.delegated
        preps.add(new_prep)
        assert preps.size(active_prep_only=True) == size + 1
        assert preps.total_delegated == expected_total_delegated

    # Case: change delegated amount of an existing P-Rep
    for i in range(size):
        prep: 'PRep' = preps.get_by_index(i)

        new_prep: 'PRep' = prep.copy()
        new_prep.delegated = random.randint(0, 5000)

        expected_total_delegated: int = \
            preps.total_delegated - prep.delegated + new_prep.delegated

        old_prep: 'PRep' = preps.replace(new_prep)
        assert id(prep) == id(old_prep)
        assert preps.total_delegated == expected_total_delegated


def test_copy(create_prep_container):
    size: int = 20
    preps: 'PRepContainer' = create_prep_container(size)

    for mutable in (True, False):
        copied_preps: 'PRepContainer' = preps.copy(mutable)
        assert preps.total_delegated == copied_preps.total_delegated

        assert len(preps._active_prep_list) == len(copied_preps._active_prep_list)
        assert len(preps._prep_dict) == len(copied_preps._prep_dict)

        for prep, prep2 in zip(preps._active_prep_list, copied_preps._active_prep_list):
            assert id(prep) == id(prep2)

        for prep, prep2 in zip(preps._prep_dict, copied_preps._prep_dict):
            assert id(prep) == id(prep2)


def test_add(create_prep_container):
    size: int = 10
    preps: 'PRepContainer' = create_prep_container(size)

    # Case: Add an active P-Rep
    new_prep = _create_dummy_prep(size)
    preps.add(new_prep)
    assert preps.size(active_prep_only=True) == size + 1
    assert preps.size(active_prep_only=False) == size + 1

    with pytest.raises(InvalidParamsException):
        preps.add(new_prep)

    index: int = 5
    prep: 'PRep' = preps.get_by_index(index)
    assert prep is not None

    for status in (PRepStatus.UNREGISTERED, PRepStatus.DISQUALIFIED):
        preps.remove(prep.address)
        assert preps.size(active_prep_only=True) == size
        assert preps.size(active_prep_only=False) == size

        prep.status = status
        preps.add(prep)
        assert preps.size(active_prep_only=True) == size
        assert preps.size(active_prep_only=False) == size + 1


def test_remove(create_prep_container):
    size: int = 10
    preps: 'PRepContainer' = create_prep_container(size)

    for i in range(size):
        prep: 'PRep' = preps.get_by_index(0)
        assert prep is not None

        preps.remove(prep.address)
        assert preps.size(active_prep_only=True) == size - i - 1
        assert preps.size(active_prep_only=False) == size - i - 1


def test_replace(create_prep_container):
    size: int = 20
    preps: 'PRepContainer' = create_prep_container(size)

    index: int = 10
    old_prep: Optional['PRep'] = preps.get_by_index(index)
    new_prep: 'PRep' = old_prep.copy()
    assert id(old_prep) != id(new_prep)

    new_prep.country = "USA"
    new_prep.city = "New York"

    preps.replace(new_prep)
    assert new_prep == preps.get_by_index(index)
    assert old_prep.address == new_prep.address
    assert index == preps.index(new_prep.address)
    assert preps.total_delegated == preps.total_delegated
    assert preps.size(active_prep_only=True) == preps.size(active_prep_only=True)
    assert preps.size(active_prep_only=False) == preps.size(active_prep_only=False)

    old_prep = preps.replace(new_prep)
    assert old_prep is None
