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
from iconservice.icon_constant import IISS_INITIAL_IREP, PenaltyReason, Revision
from iconservice.prep.data.prep import PRep, PRepDictType

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
TOTAL_BLOCKS = 0
VALIDATED_BLOCKS = 0
IREP_BLOCK_HEIGHT = BLOCK_HEIGHT
PENALTY = PenaltyReason.BLOCK_VALIDATION
UNVALIDATED_SEQUENCE_BLOCKS = 10


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
        prep.update_block_statistics(is_validator=True)


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


def test_from_bytes_and_to_bytes_with_revision_iiss(prep):
    data = prep.to_bytes(Revision.IISS.value)
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
    assert prep.penalty == PENALTY
    assert prep2.penalty == PenaltyReason.NONE
    assert prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS

    # Properties which is not serialized in PRep.to_bytes()
    assert prep2.stake == 0
    assert prep2.delegated == 0


def test_from_bytes_and_to_bytes_with_revision_decentralization(prep):
    data = prep.to_bytes(Revision.DECENTRALIZATION.value)
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


def test_is_suspended(prep):
    prep.penalty = PenaltyReason.NONE
    assert not prep.is_suspended()

    prep.penalty = PenaltyReason.LOW_PRODUCTIVITY
    assert not prep.is_suspended()

    prep.penalty = PenaltyReason.BLOCK_VALIDATION
    assert prep.penalty == PenaltyReason.BLOCK_VALIDATION
    assert prep.is_suspended()


def test_update_block_statistics(prep):
    assert prep.total_blocks == 0
    assert prep.validated_blocks == 0
    assert prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS

    prep.update_block_statistics(is_validator=False)
    assert prep.total_blocks == 1
    assert prep.validated_blocks == 0
    assert prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS + 1

    prep.update_block_statistics(is_validator=True)
    assert prep.total_blocks == 2
    assert prep.validated_blocks == 1
    assert prep.unvalidated_sequence_blocks == 0


def test_reset_block_validation_penalty(prep):
    size = 100

    for _ in range(size):
        prep.update_block_statistics(is_validator=False)

    assert prep.total_blocks == size
    assert prep.validated_blocks == 0
    assert prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS + size

    prep.penalty = PenaltyReason.BLOCK_VALIDATION
    assert prep.penalty == PenaltyReason.BLOCK_VALIDATION

    prep.reset_block_validation_penalty()
    assert prep.penalty == PenaltyReason.NONE
    assert prep.unvalidated_sequence_blocks == 0


def test_to_dict_with_full(prep):
    info: dict = prep.to_dict(PRepDictType.FULL)

    assert info["address"] == prep.address
    assert info["name"] == prep.name == NAME
    assert info["status"] == prep.status.value
    assert info["grade"] == prep.grade.value
    assert info["country"] == prep.country == COUNTRY
    assert info["city"] == prep.city == CITY
    assert info["email"] == prep.email == EMAIL
    assert info["website"] == prep.website == WEBSITE
    assert info["details"] == prep.details == DETAILS
    assert info["p2pEndpoint"] == prep.p2p_endpoint == P2P_END_POINT
    assert info["irep"] == prep.irep == IREP
    assert info["irepUpdateBlockHeight"] == prep.irep_block_height == BLOCK_HEIGHT
    assert info["stake"] == prep.stake == STAKE
    assert info["delegated"] == prep.delegated == DELEGATED
    assert info["totalBlocks"] == prep.total_blocks == TOTAL_BLOCKS
    assert info["validatedBlocks"] == prep.validated_blocks == VALIDATED_BLOCKS
    assert info["penalty"] == prep.penalty.value == PENALTY.value
    assert info["unvalidatedSequenceBlocks"] == prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS
    assert info["blockHeight"] == prep.block_height
    assert info["txIndex"] == prep.tx_index

    # SIZE(20) - 1(version) + 2(stake, delegated) = 21
    assert len(info) == PRep.Index.SIZE + 1


def test_to_dict_with_abridged(prep):
    info: dict = prep.to_dict(PRepDictType.ABRIDGED)

    assert info["address"] == prep.address
    assert info["name"] == prep.name == NAME
    assert info["status"] == prep.status.value
    assert info["grade"] == prep.grade.value
    assert info["country"] == prep.country == COUNTRY
    assert info["city"] == prep.city == CITY
    assert "email" not in info
    assert "website" not in info
    assert "details" not in info
    assert "p2pEndpoint" not in info
    assert info["irep"] == prep.irep == IREP
    assert info["irepUpdateBlockHeight"] == prep.irep_block_height == BLOCK_HEIGHT
    assert info["stake"] == prep.stake == STAKE
    assert info["delegated"] == prep.delegated == DELEGATED
    assert info["totalBlocks"] == prep.total_blocks == TOTAL_BLOCKS
    assert info["validatedBlocks"] == prep.validated_blocks == VALIDATED_BLOCKS
    assert info["penalty"] == prep.penalty.value == PENALTY.value
    assert info["unvalidatedSequenceBlocks"] == prep.unvalidated_sequence_blocks == UNVALIDATED_SEQUENCE_BLOCKS
    assert info["blockHeight"] == prep.block_height
    assert info["txIndex"] == prep.tx_index

    # version, email, website, details and p2pEndpoint are not included
    # SIZE(20) - 5(version, email, website, details, p2pEndpoint) + 2(stake, delegated)
    assert len(info) == PRep.Index.SIZE - 3
