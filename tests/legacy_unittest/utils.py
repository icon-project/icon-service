# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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
import time
from typing import Optional

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.block import Block
from iconservice.icon_constant import PRepStatus, PRepGrade
from iconservice.prep.data import PRep, PRepContainer
from iconservice.utils import icx_to_loop


def create_dummy_prep(
    index: int,
    address: Optional["Address"] = None,
    status: "PRepStatus" = PRepStatus.ACTIVE,
) -> "PRep":
    address = address if address else Address(AddressPrefix.EOA, os.urandom(20))

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
        block_height=index,
    )


def create_dummy_preps(
    size: int, main_preps: int, elected_preps: int
) -> "PRepContainer":
    assert elected_preps <= size <= 1000

    preps = PRepContainer()

    # Create dummy preps
    for i in range(size):
        address = Address.from_prefix_and_int(AddressPrefix.EOA, i)
        delegated = icx_to_loop(1000 - i)

        if i < main_preps:
            grade = PRepGrade.MAIN
        elif i < elected_preps:
            grade = PRepGrade.SUB
        else:
            grade = PRepGrade.CANDIDATE

        prep = PRep(address, grade=grade, block_height=i, delegated=delegated)
        prep.freeze()

        assert prep.grade == grade
        assert prep.delegated == delegated
        assert prep.block_height == i
        preps.add(prep)

    assert preps.size(active_prep_only=True) == size
    assert preps.size(active_prep_only=False) == size

    return preps


def get_timestamp_us() -> int:
    return int(time.time() * 1_000_000)


def create_dummy_block(block_height: int = -1) -> "Block":
    block_height: int = block_height if block_height >= 0 else random.randint(
        100, 10000
    )
    block_hash: bytes = os.urandom(32)
    timestamp_us: int = get_timestamp_us()
    prev_hash: bytes = os.urandom(32)

    return Block(block_height, block_hash, timestamp_us, prev_hash)
