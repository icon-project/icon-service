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
from iconservice.prep.data import PRep, PRepFlag


def test_frozen_flag():
    address = Address(AddressPrefix.EOA, os.urandom(20))
    prep = PRep(address, flags=PRepFlag.FROZEN)

    with pytest.raises(AccessDeniedException):
        prep.delegated = 100


def test_set_ok():
    address = Address(AddressPrefix.EOA, os.urandom(20))
    prep = PRep(address)

    assert prep.name == ""
    assert prep.email == ""
    assert prep.website == ""
    assert prep.details == ""
    assert prep.p2p_end_point == ""
    assert prep.irep == 0
    assert prep.irep_block_height == 0

    kwargs = {
        "name": "Best P-Rep",
        "email": "best@example.com",
        "website": "https://node.example.com",
        "details": "https://node.example.com/details",
        "p2p_end_point": "https://node.example.com:7100",
        "irep": 10_000,
        "irep_block_height": 1234,
    }

    prep.set(**kwargs)
    assert prep.name == kwargs["name"]
    assert prep.email == kwargs["email"]
    assert prep.website == kwargs["website"]
    assert prep.details == kwargs["details"]
    assert prep.p2p_end_point == kwargs["p2p_end_point"]
    assert prep.irep == kwargs["irep"]
    assert prep.irep_block_height == kwargs["irep_block_height"]
