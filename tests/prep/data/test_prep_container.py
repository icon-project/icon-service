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
import hashlib
import random
from typing import Optional

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.prep.data import PRep, PRepContainer
from iconservice.base.exception import AccessDeniedException


@pytest.fixture
def create_prep_container():

    def _create_prep_container(size: int = 100):
        preps = PRepContainer()

        for i in range(size):
            address = Address(AddressPrefix.EOA, os.urandom(20))
            prep = PRep(
                address=address,
                name=f"node{i}",
                email=f"node{i}@example.com",
                website=f"https://node{i}.example.com",
                details=f"https://node{i}.example.com/details",
                p2p_end_point=f"https://node{i}.example.com:7100",
                public_key=hashlib.sha3_256(address.to_bytes()).digest(),
                delegated=random.randint(0, 1000),
                irep=10_000,
                irep_block_height=i,
                block_height=i
            )

            preps.add(prep)

        return preps

    return _create_prep_container


def test_add(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)
    assert len(preps) == size

    prev_prep: Optional['PRep'] = None
    for prep in preps:
        if prev_prep:
            assert prev_prep.order() < prep.order()

        prev_prep = prep
        print(f"{prep.order()}")


def test_getitem(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)
    assert len(preps) == size

    for i in range(size):
        prep_by_index: 'PRep' = preps.get_by_index(i)
        prep_by_address: 'PRep' = preps.get_by_address(prep_by_index.address)
        assert prep_by_index == prep_by_address
        assert id(prep_by_index) == id(prep_by_address)


def test_remove(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)
    assert len(preps) == size

    for _ in range(50):
        i = random.randint(0, size-1)
        prep = preps.get_by_index(i)
        assert prep.address in preps

        removed_prep = preps.remove(prep.address)
        size -= 1

        assert prep == removed_prep
        assert prep.address not in preps
        assert len(preps) == size


def test_index(create_prep_container):
    size: int = 100
    preps = create_prep_container(size)
    assert len(preps) == size

    i = random.randint(0, size - 1)
    prep = preps.get_by_index(i)

    index: int = preps.index(prep.address)
    assert 0 <= index < size
    assert prep == preps.get_by_index(index)


def test_freeze(create_prep_container):
    size: int = 100
    preps: 'PRepContainer' = create_prep_container(size)
    assert len(preps) == size

    preps.freeze()

    i = random.randint(0, size - 1)
    prep = preps.get_by_index(i)

    with pytest.raises(AccessDeniedException):
        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        preps.add(PRep(address))

    with pytest.raises(AccessDeniedException):
        preps.remove(prep.address)
