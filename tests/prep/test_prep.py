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

import pytest

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.exception import AccessDeniedException
from iconservice.icon_constant import IISS_INITIAL_IREP, PenaltyReason, REV_DECENTRALIZATION
from iconservice.prep.data import PRep

NAME = "banana"
EMAIL = "banana@example.com"
COUNTRY = "KOR"
CITY = "Seoul"
WEBSITE = "https://banana.example.com"
DETAILS = "https://banana.example.com/details"
P2P_END_POINT = "banana.example.com:7100"
IREP = IISS_INITIAL_IREP
LAST_GENERATE_BLOCK_HEIGHT = 50
STAKE = 100
DELEGATED = 100
BLOCK_HEIGHT = 777
TX_INDEX = 0
TOTAL_BLOCKS = 1000
VALIDATED_BLOCKS = 900
IREP_BLOCK_HEIGHT = BLOCK_HEIGHT
PENALTY = PenaltyReason.LOW_PRODUCTIVITY
UNVALIDATED_SEQUENCE_BLOCKS = 100


@pytest.fixture
def prep():
    address = Address(AddressPrefix.EOA, os.urandom(20))
    prep = PRep(
        address,
        name=NAME,
        country=COUNTRY,
        city=CITY,
        email=EMAIL,
        website=WEBSITE,
        details=DETAILS,
        p2p_endpoint=P2P_END_POINT,
        irep=IREP,
        irep_block_height=IREP_BLOCK_HEIGHT,
        last_generate_block_height=LAST_GENERATE_BLOCK_HEIGHT,
        stake=STAKE,
        delegated=DELEGATED,
        block_height=BLOCK_HEIGHT,
        tx_index=TX_INDEX,
        total_blocks=TOTAL_BLOCKS,
        validated_blocks=VALIDATED_BLOCKS,
        penalty=PENALTY,
        unvalidated_sequence_blocks=UNVALIDATED_SEQUENCE_BLOCKS
    )

    assert prep.address == address
    assert prep.name == NAME
    # "ZZZ" is the 3-letter country code that means unknown country
    assert prep.country == "KOR"
    assert prep.city == CITY
    assert prep.email == EMAIL
    assert prep.website == WEBSITE
    assert prep.details == DETAILS
    assert prep.p2p_endpoint == P2P_END_POINT
    assert prep.irep == IREP
    assert prep.irep_block_height == BLOCK_HEIGHT
    assert prep.stake == STAKE
    assert prep.delegated == DELEGATED
    assert prep.total_blocks == TOTAL_BLOCKS
    assert prep.validated_blocks == VALIDATED_BLOCKS
    assert prep.penalty == PENALTY
    assert prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS

    return prep


def test_freeze(prep):
    assert not prep.is_frozen()

    fixed_name = "orange"
    prep.set(name=fixed_name)
    assert prep.name == fixed_name

    prep.freeze()
    assert prep.is_frozen()

    with pytest.raises(AccessDeniedException):
        prep.set(name="candy")
    assert prep.name == fixed_name

    with pytest.raises(AccessDeniedException):
        prep.set_irep(10_000, 777)

    with pytest.raises(AccessDeniedException):
        prep.update_main_prep_validate(True)


def test_set_ok(prep):
    kwargs = {
        "name": "Best P-Rep",
        "country": "KOR",
        "city": "Seoul",
        "email": "best@example.com",
        "website": "https://node.example.com",
        "details": "https://node.example.com/details",
        "p2p_endpoint": "node.example.com:7100",
    }

    prep.set(**kwargs)
    assert prep.name == kwargs["name"]
    assert prep.country == kwargs["country"]
    assert prep.city == kwargs["city"]
    assert prep.email == kwargs["email"]
    assert prep.website == kwargs["website"]
    assert prep.details == kwargs["details"]
    assert prep.p2p_endpoint == kwargs["p2p_endpoint"]


def test_set_error(prep):
    kwargs = {
        "irep": IREP + 1,
        "irep_block_height": BLOCK_HEIGHT + 1,
    }

    with pytest.raises(TypeError):
        prep.set(**kwargs)


def test_from_bytes_and_to_bytes(prep):
    data = prep.to_bytes(REV_DECENTRALIZATION)
    prep2 = PRep.from_bytes(data)

    assert prep.address == prep2.address
    assert prep.name == prep2.name == NAME
    assert prep.country == prep2.country == COUNTRY
    assert prep.city == prep2.city == CITY
    assert prep.email == prep2.email == EMAIL
    assert prep.website == prep2.website == WEBSITE
    assert prep.details == prep2.details == DETAILS
    assert prep.p2p_endpoint == prep2.p2p_endpoint == P2P_END_POINT
    assert prep.irep == prep2.irep == IREP
    assert prep.irep_block_height == prep2.irep_block_height == IREP_BLOCK_HEIGHT
    assert prep.last_generate_block_height == prep2.last_generate_block_height == LAST_GENERATE_BLOCK_HEIGHT
    assert prep.total_blocks == prep2.total_blocks == TOTAL_BLOCKS
    assert prep.validated_blocks == prep2.validated_blocks == VALIDATED_BLOCKS
    assert prep.penalty == prep2.penalty == PENALTY
    assert prep.unvalidated_sequence_blocks == prep2.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS

    # Properties which is not serialized in PRep.to_bytes()
    assert prep2.stake == 0
    assert prep2.delegated == 0


def test_country(prep):
    assert prep.country == COUNTRY

    for code in "Usa", "uSa", "usA", "uSA", "UsA", "USa", "usa", "USA":
        prep.country = code
        assert prep.country == "USA"

    prep.country = "hello"
    assert prep.country == "ZZZ"
