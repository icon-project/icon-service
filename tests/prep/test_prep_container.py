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
from typing import Optional

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import AccessDeniedException
from iconservice.prep.data import PRep, PRepContainer, PRepStatus


def _create_dummy_prep(index: int) -> 'PRep':
    address = Address(AddressPrefix.EOA, os.urandom(20))
    public_key: bytes = b"\x04" + os.urandom(64)

    return PRep(
        address=address,
        name=f"node{index}",
        email=f"node{index}@example.com",
        website=f"https://node{index}.example.com",
        details=f"https://node{index}.example.com/details",
        p2p_endpoint=f"https://node{index}.example.com:7100",
        public_key=public_key,
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

        assert len(preps) == size
        return preps

    return _create_prep_container


def test_add(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    prev_prep: Optional['PRep'] = None
    for prep in preps:
        if prev_prep:
            assert prev_prep.order() < prep.order()

        prev_prep = prep
        print(f"{prep.order()}")


def test_getitem(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    for i in range(size):
        prep_by_index: 'PRep' = preps.get_by_index(i)
        prep_by_address: 'PRep' = preps.get_by_address(prep_by_index.address)
        assert prep_by_index == prep_by_address
        assert id(prep_by_index) == id(prep_by_address)


def test_get_by_address_with_non_existing_address(create_prep_container):
    size = 10
    preps = create_prep_container(size)

    index: int = random.randint(0, size - 1)
    prep: 'PRep' = preps.get_by_index(index)
    assert isinstance(prep, PRep)

    removed_prep = preps.remove(prep.address)

    prep = preps.get_by_address(removed_prep.address, mutable=False)
    assert prep is None

    prep = preps.get_by_address(removed_prep.address, mutable=True)
    assert prep is None


def test_get_by_index(create_prep_container):
    size = 10
    preps = create_prep_container(size)

    index: int = random.randint(0, size - 1)
    prep: 'PRep' = preps.get_by_index(index)
    assert isinstance(prep, PRep)

    prep = preps.get_by_index(size, mutable=False)
    assert prep is None

    prep = preps.get_by_index(size, mutable=True)
    assert prep is None

    for i in range(1, size + 1):
        prep = preps.get_by_index(-i)
        assert prep is not None
        assert prep == preps.get_by_index(size - i)


def test_get_inactive_prep_by_address(create_prep_container):
    size = 11
    preps = create_prep_container(size)

    for prep_status in (PRepStatus.UNREGISTERED, PRepStatus.PENALTY1, PRepStatus.PENALTY2):
        # Make sure that the prep to remove is active
        index: int = random.randint(0, len(preps) - 1)
        prep: 'PRep' = preps.get_by_index(index)
        assert isinstance(prep, PRep)
        assert prep.status == PRepStatus.ACTIVE
        assert not prep.is_frozen()

        # Remove a prep from PRepContainer with a given index
        removed_prep = preps.remove(prep.address, prep_status)
        assert id(prep) == id(removed_prep)
        assert removed_prep.is_frozen()
        assert removed_prep.address not in preps
        assert preps.contains(removed_prep.address, inactive_preps_included=True)

        # Check whether the prep is removed
        active_prep: 'PRep' = preps.get_by_address(removed_prep.address)
        assert active_prep is None

        # Get the prep from preps._inactive_prep_list
        inactive_preps: 'PRep' = preps.get_inactive_prep_by_address(removed_prep.address)
        assert inactive_preps is not None
        assert id(inactive_preps) == id(removed_prep)
        assert inactive_preps.status == prep_status


def test_remove(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    for _ in range(50):
        i = random.randint(0, size-1)
        prep = preps.get_by_index(i)
        assert prep.address in preps

        removed_prep = preps.remove(prep.address)
        size -= 1

        assert prep == removed_prep
        assert prep.address not in preps
        assert len(preps) == size
        assert removed_prep.address not in preps
        assert preps.contains(removed_prep.address, inactive_preps_included=True)


def test_index(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)

    i = random.randint(0, size - 1)
    prep = preps.get_by_index(i)

    index: int = preps.index(prep.address)
    assert 0 <= index < size
    assert prep == preps.get_by_index(index)


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


def test_total_prep_delegated(create_prep_container):
    size: int = 51
    preps: 'PRepContainer' = create_prep_container(size)

    total_delegated: int = 0
    for prep in preps:
        total_delegated += prep.delegated

    assert total_delegated == preps.total_prep_delegated

    # Case: remove a P-Rep
    for _ in range(size // 2):
        index: int = random.randint(0, len(preps) - 1)
        prep: 'PRep' = preps.get_by_index(index)

        expected_total_prep_delegated: int = preps.total_prep_delegated - prep.delegated
        preps.remove(prep.address)
        assert preps.total_prep_delegated == expected_total_prep_delegated

    # Case: add a P-Rep
    for _ in range(size // 2):
        index: int = len(preps)
        new_prep: 'PRep' = _create_dummy_prep(index)

        expected_total_prep_delegated: int = preps.total_prep_delegated + new_prep.delegated
        preps.add(new_prep)
        assert preps.total_prep_delegated == expected_total_prep_delegated

    assert len(preps) == size

    # Case: change delegated amount of an existing P-Rep
    for i in range(size):
        prep: 'PRep' = preps.get_by_index(i)
        new_delegated: int = random.randint(0, 5000)

        expected_total_prep_delegated: int = \
            preps.total_prep_delegated - prep.delegated + new_delegated
        preps.set_delegated_to_prep(prep.address, new_delegated)
        assert prep.delegated == new_delegated
        assert preps.total_prep_delegated == expected_total_prep_delegated


def test_copy(create_prep_container):
    size: int = 20
    preps: 'PRepContainer' = create_prep_container(size)

    for mutable in (True, False):
        copied_preps: 'PRepContainer' = preps.copy(mutable)
        assert preps.total_prep_delegated == copied_preps.total_prep_delegated

        assert len(preps._active_prep_list) == len(copied_preps._active_prep_list)
        assert len(preps._active_prep_dict) == len(copied_preps._active_prep_dict)
        assert len(preps._inactive_prep_dict) == len(copied_preps._inactive_prep_dict)

        for prep, prep2 in zip(preps._active_prep_list, copied_preps._active_prep_list):
            assert id(prep) == id(prep2)

        for prep, prep2 in zip(preps._active_prep_dict, copied_preps._active_prep_dict):
            assert id(prep) == id(prep2)

        for prep, prep2 in zip(preps._inactive_prep_dict, preps._inactive_prep_dict):
            assert id(prep) == id(prep2)
