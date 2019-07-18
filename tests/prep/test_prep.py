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
from iconservice.prep.data import PRep

NAME = "banana"
EMAIL = "banana@example.com"
WEBSITE = "https://banana.example.com"
DETAILS = "https://banana.example.com/details"
P2P_END_POINT = "https://banana.example.com:7100"
IREP = 10_000
BLOCK_HEIGHT = 777
TX_INDEX = 0


@pytest.fixture
def prep():
    address = Address(AddressPrefix.EOA, os.urandom(20))
    prep = PRep(
        address,
        name=NAME,
        email=EMAIL,
        website=WEBSITE,
        details=DETAILS,
        p2p_endpoint=P2P_END_POINT,
        irep=IREP,
        irep_block_height=BLOCK_HEIGHT,
        block_height=BLOCK_HEIGHT,
        tx_index=TX_INDEX
    )

    assert prep.name == NAME
    # "ZZZ" is the 3-letter country code that means unknown country
    assert prep.country == "ZZZ"
    assert prep.email == EMAIL
    assert prep.website == WEBSITE
    assert prep.details == DETAILS
    assert prep.p2p_endpoint == P2P_END_POINT

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
        prep.update_productivity(True)


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
