# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from __future__ import annotations

import os
from typing import Iterable, Tuple, Optional, TypeVar
from unittest.mock import Mock

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidContainerAccessException
from iconservice.database.db import ContextDatabase
from iconservice.icon_constant import Revision
from iconservice.iconscore.db import (
    IconScoreDatabase,
    Key,
    ContainerTag,
)
from iconservice.iconscore.icon_container_db import (
    ArrayDB,
    DictDB,
    VarDB,
)
from iconservice.utils import int_to_bytes
from iconservice.utils.rlp import rlp_encode_bytes


class DummyKeyValueDatabase:
    def __init__(self):
        self._db = {}

    def get(self, key: bytes) -> bytes:
        return self._db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        self._db[key] = value

    def delete(self, key: bytes) -> None:
        if key in self._db:
            del self._db[key]

    def close(self) -> None:
        self._db = None

    def get_sub_db(self, prefix: bytes) -> DummyKeyValueDatabase:
        raise NotImplemented

    def iterator(self) -> iter:
        return iter(self._db)

    def write_batch(self, it: Iterable[Tuple[bytes, Optional[bytes]]]) -> int:
        raise NotImplemented


@pytest.fixture(scope="function")
def key_value_db() -> DummyKeyValueDatabase:
    return DummyKeyValueDatabase()


K = TypeVar("K", bytes, Key, ContainerTag, Address)


def _to_bytes(key: K) -> bytes:
    if isinstance(key, (ContainerTag, Key)):
        return key.value
    elif isinstance(key, Address):
        return key.to_bytes()
    elif isinstance(key, bytes):
        return key

    raise ValueError


def _get_final_key(*args, use_rlp: bool) -> bytes:
    keys = (_to_bytes(key) for key in args)

    if use_rlp:
        return _get_final_key_with_rlp(*keys)
    else:
        return _get_final_key_with_pipe(*keys)


def _get_final_key_with_pipe(*args) -> bytes:
    return b"|".join((key for key in args))


def _get_final_key_with_rlp(*args) -> bytes:
    return args[0] + b"".join((rlp_encode_bytes(key) for key in args[1:]))


class TestIconScoreDatabase:

    @classmethod
    def _init_context(cls, context, address: 'Address'):
        context.current_address = address
        context._inv_container = Mock()

    @classmethod
    def _set_revision(cls, context, revision: int):
        context._inv_container.revision_code = revision

    def test_array_db(self, context, key_value_db):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(address, context_db)

        self._init_context(context, score_db.address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "balances"
        balances = ArrayDB(name, score_db, int)

        for i in range(2):
            balances.put(i * 100)
        assert len(balances) == 2

        self._set_revision(context, Revision.USE_RLP.value)

        balances.put(200)  # balances[2] = 200
        balances.put(300)  # balances[3] = 300
        assert len(balances) == 4

        # balances: [0, 100, 200, 300]
        for i, value in enumerate(balances):
            assert value == i * 100

        # len(balances)
        final_key: bytes = _get_final_key(address, ContainerTag.ARRAY, name.encode(), use_rlp=True)
        assert key_value_db.get(final_key) == int_to_bytes(len(balances))

        for i, use_rlp in enumerate((False, False, True, True)):
            key = _get_final_key(
                address.to_bytes(),
                ContainerTag.ARRAY.value,
                name.encode(),
                int_to_bytes(i),
                use_rlp=use_rlp,
            )
            assert key_value_db.get(key) == int_to_bytes(i * 100)

    def test_var_db(self, context, key_value_db):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(address, context_db)

        self._init_context(context, address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "owner"
        owner_address = Address(AddressPrefix.EOA, os.urandom(20))

        owner = VarDB(name, score_db, Address)
        owner.set(owner_address)
        assert owner.get() == owner_address

        key = _get_final_key(address, ContainerTag.VAR, name.encode(), use_rlp=False)
        assert key_value_db.get(key) == owner_address.to_bytes()

        self._set_revision(context, Revision.USE_RLP.value)
        assert key_value_db.get(key) == owner_address.to_bytes()

        owner.set(address)
        assert owner.get() == address
        assert owner.get() != owner_address

        key = _get_final_key(address, ContainerTag.VAR, name.encode(), use_rlp=True)
        assert key_value_db.get(key) == address.to_bytes()

    def test_1_depth_dict_db(self, context, key_value_db):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        score_address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(score_address, context_db)

        addresses = [
            Address(AddressPrefix.EOA, i.to_bytes(20, "big"))
            for i in range(3)
        ]

        self._init_context(context, score_address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "balances"
        balances = DictDB(name, score_db, depth=1, value_type=int)

        # [0, 100]
        for i in range(2):
            balance = i * 100
            address = addresses[i]
            balances[address] = balance
            assert balances[address] == balance

            key = _get_final_key(
                score_address, ContainerTag.DICT, name.encode(), address,
                use_rlp=False
            )
            assert key_value_db.get(key) == int_to_bytes(balance)

        self._set_revision(context, Revision.USE_RLP.value)

        # [0, 1000, 2000]
        for i in range(1, 3):
            balance = i * 1000
            address = addresses[i]
            balances[address] = balance
            assert balances[address] == balance

            key = _get_final_key(
                score_address, ContainerTag.DICT, name.encode(), address,
                use_rlp=True
            )
            assert key_value_db.get(key) == int_to_bytes(balance)

        # [0, 1000, 2000]
        for i, address in enumerate(addresses):
            assert balances[address] == i * 1000

        # {0, 2000}
        del balances[addresses[1]]
        assert balances[addresses[1]] == 0

    def test_2_depth_dict_db(self, context, key_value_db):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        score_address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(score_address, context_db)

        self._init_context(context, score_address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        # allowances[Address][Address] = int
        name = "allowances"
        allowances = DictDB(name, score_db, depth=2, value_type=int)

        parents = [
            Address.from_prefix_and_int(AddressPrefix.EOA, 0),
            Address.from_prefix_and_int(AddressPrefix.EOA, 1)
        ]

        children = [
            Address.from_prefix_and_int(AddressPrefix.EOA, 100),
            Address.from_prefix_and_int(AddressPrefix.EOA, 101)
        ]

        expected_allowances = {
            parents[0]: {
                children[0]: 100,
                children[1]: 200,
            },
            parents[1]: {
                children[0]: 1000,
                children[1]: 2000,
            },
        }

        for parent in parents:
            for child in children:
                allowances[parent][child] = expected_allowances[parent][child]

        for parent in parents:
            for child in children:
                expected_allowance = expected_allowances[parent][child]
                assert allowances[parent][child] == expected_allowance

                key = _get_final_key(
                    score_address,
                    ContainerTag.DICT, name.encode(),
                    ContainerTag.DICT, parent.to_bytes(),
                    child.to_bytes(),
                    use_rlp=False
                )
                assert key_value_db.get(key) == int_to_bytes(expected_allowance)

        with pytest.raises(InvalidContainerAccessException):
            del allowances[parents[0]]

        del allowances[parents[0]][children[0]]
        assert allowances[parents[0]][children[0]] == 0

        self._set_revision(context, Revision.USE_RLP.value)

        value = 9999
        allowances[parents[0]][children[0]] = value
        assert allowances[parents[0]][children[0]] == value

        key = _get_final_key(
            score_address,
            ContainerTag.DICT, name.encode(),
            parents[0].to_bytes(), children[0].to_bytes(),
            use_rlp=True
        )
        assert key_value_db.get(key) == int_to_bytes(value)
