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
    ContainerUtil,
    get_default_value,
)
from iconservice.utils import int_to_bytes
from iconservice.utils.rlp import rlp_encode_bytes


class DummyKeyValueDatabase:
    def __init__(self):
        self._db = {}

    def __len__(self):
        return len(self._db)

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

    @pytest.mark.parametrize(
        "values,value_type",
        [
            ((0, 100, 200, 300), int),
            (("aa", "b", "ccc", "dddd"), str),
            ((b"aa", b"b", b"ccc", b"dddd"), bytes),
            ((True, False, True, False), bool),
            ([Address(AddressPrefix.EOA, os.urandom(20)) for _ in range(4)], Address),
        ]
    )
    def test_array_db(self, context, key_value_db, values, value_type):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(address, context_db)

        self._init_context(context, score_db.address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "array_db"
        array_db = ArrayDB(name, score_db, value_type)

        for i in range(2):
            array_db.put(values[i])
        assert len(array_db) == 2

        self._set_revision(context, Revision.USE_RLP.value)

        array_db.put(values[2])
        array_db.put(values[3])
        assert len(array_db) == 4

        for i, value in enumerate(array_db):
            assert value == values[i]

        final_key: bytes = _get_final_key(address, ContainerTag.ARRAY, name.encode(), use_rlp=True)
        assert key_value_db.get(final_key) == int_to_bytes(len(array_db))

        for i, use_rlp in enumerate((False, False, True, True)):
            key = _get_final_key(
                address.to_bytes(),
                ContainerTag.ARRAY.value,
                name.encode(),
                int_to_bytes(i),
                use_rlp=use_rlp,
            )
            assert key_value_db.get(key) == ContainerUtil.encode_value(values[i])

        for v in reversed(values):
            assert v == array_db.pop()
        assert len(array_db) == 0

        # 2 values for array_db size still remain
        # even though all items in array_db have been popped.
        assert len(key_value_db) == 2

    @pytest.mark.parametrize(
        "old_value,new_value,value_type",
        [
            (300, 500, int),
            ("old string", "new string", str),
            (b"old", b"new", bytes),
            (False, True, bool),
            (
                Address(AddressPrefix.EOA, os.urandom(20)),
                Address(AddressPrefix.CONTRACT, os.urandom(20)),
                Address,
            ),
        ]
    )
    def test_var_db(self, context, key_value_db, old_value, new_value, value_type):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(address, context_db)

        self._init_context(context, address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "var_db"

        var_db = VarDB(name, score_db, value_type)
        var_db.set(old_value)
        assert var_db.get() == old_value

        key = _get_final_key(address, ContainerTag.VAR, name.encode(), use_rlp=False)
        assert key_value_db.get(key) == ContainerUtil.encode_value(old_value)

        self._set_revision(context, Revision.USE_RLP.value)
        assert key_value_db.get(key) == ContainerUtil.encode_value(old_value)

        var_db.set(new_value)
        assert var_db.get() == new_value
        assert var_db.get() != old_value

        key = _get_final_key(address, ContainerTag.VAR, name.encode(), use_rlp=True)
        assert key_value_db.get(key) == ContainerUtil.encode_value(new_value)

        var_db.remove()
        assert var_db.get() == get_default_value(value_type)
        assert len(key_value_db) == 0

    @pytest.mark.parametrize(
        "keys",
        [
            (b"hello", 1234, "world", Address(AddressPrefix.EOA, os.urandom(20))),
        ]
    )
    @pytest.mark.parametrize(
        "old_values, new_values, value_type",
        [
            ((False, True, False, True), (True, False, True, False), bool),
            ((b"a", b"b", b"c", b"d"), (b"A", b"B", b"C", b"D"), bytes),
            ((10, 20, 30, 40), (100, 200, 300, 400), int),
            (("aa", "bb", "cc", "dd"), ("AA", "BB", "CC", "DD"), str),
            (
                [Address(AddressPrefix.EOA, os.urandom(20)) for _ in range(4)],
                [Address(AddressPrefix.CONTRACT, os.urandom(20)) for _ in range(4)],
                Address
            ),
        ]
    )
    def test_1_depth_dict_db(self, context, key_value_db, keys, old_values, new_values, value_type):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        score_address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(score_address, context_db)

        self._init_context(context, score_address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "dict_db_depth_1"
        dict_db = DictDB(name, score_db, depth=1, value_type=value_type)

        # Put two items to dict_db
        for i in range(2):
            k, v = keys[i], old_values[i]

            dict_db[k] = v
            assert dict_db[k] == v

            key = _get_final_key(
                score_address, ContainerTag.DICT, name.encode(), ContainerUtil.encode_key(k),
                use_rlp=False
            )
            assert key_value_db.get(key) == ContainerUtil.encode_value(v)

        self._set_revision(context, Revision.USE_RLP.value)

        # Read old-formatted data on Revision.USE_RLP
        for i in range(2):
            k, v = keys[i], old_values[i]
            assert dict_db[k] == v

            key = _get_final_key(
                score_address, ContainerTag.DICT, name.encode(), ContainerUtil.encode_key(k),
                use_rlp=False
            )
            assert key_value_db.get(key) == ContainerUtil.encode_value(v)

        # Put 4 items to dict_db
        for i, k in enumerate(keys):
            old_v = old_values[i]
            new_v = new_values[i]
            dict_db[k] = new_v
            assert dict_db[k] == new_v
            assert dict_db[k] != old_v

            key = _get_final_key(
                score_address, ContainerTag.DICT, name.encode(), ContainerUtil.encode_key(k),
                use_rlp=True
            )
            assert key_value_db.get(key) == ContainerUtil.encode_value(new_v)

        # If there is no value for a given key, default value is returned
        for k in keys:
            del dict_db[k]
            assert dict_db[k] == get_default_value(value_type)

        assert len(key_value_db) == 0

    @pytest.mark.parametrize(
        "keys1",
        [
            (b"hello", 1234, "world", Address(AddressPrefix.EOA, os.urandom(20))),
        ]
    )
    @pytest.mark.parametrize(
        "keys2",
        [
            (b"hello2", 12345, "world2", Address(AddressPrefix.CONTRACT, os.urandom(20))),
        ]
    )
    @pytest.mark.parametrize(
        "old_values, new_values, value_type",
        [
            ((False, True, False, True), (True, False, True, False), bool),
            ((b"a", b"b", b"c", b"d"), (b"A", b"B", b"C", b"D"), bytes),
            ((10, 20, 30, 40), (100, 200, 300, 400), int),
            (("aa", "bb", "cc", "dd"), ("AA", "BB", "CC", "DD"), str),
            (
                [Address(AddressPrefix.EOA, os.urandom(20)) for _ in range(4)],
                [Address(AddressPrefix.CONTRACT, os.urandom(20)) for _ in range(4)],
                Address
            ),
        ]
    )
    def test_2_depth_dict_db(self, context, key_value_db, keys1, keys2, old_values, new_values, value_type):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        score_address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(score_address, context_db)

        self._init_context(context, score_address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        name = "dict_db_depth_2"
        dict_db = DictDB(name, score_db, depth=2, value_type=value_type)

        # To assign a value to middle-layer dict_db is forbidden
        for k1, v in zip(keys1, old_values):
            with pytest.raises(InvalidContainerAccessException):
                dict_db[k1] = v

        # Assign values to dict_db on Revision.USE_RLP - 1
        for k1 in keys1:
            for k2, v in zip(keys2, old_values):
                dict_db[k1][k2] = v

        assert len(key_value_db) == len(keys1) * len(keys2)

        for k1 in keys1:
            for k2, v in zip(keys2, old_values):
                assert dict_db[k1][k2] == v

                key: bytes = _get_final_key(
                    score_address,
                    ContainerTag.DICT, name.encode(),
                    ContainerTag.DICT, ContainerUtil.encode_key(k1),
                    ContainerUtil.encode_key(k2),
                    use_rlp=False
                )
                assert key_value_db.get(key) == ContainerUtil.encode_value(v)

        self._set_revision(context, Revision.USE_RLP.value)

        # Check if reading old-formatted key:value data works on Revision.USE_RLP
        for k1 in keys1:
            for k2, v in zip(keys2, old_values):
                assert dict_db[k1][k2] == v

        # Replace all old_values with new_values on Revision.USE_RLP
        for k1 in keys1:
            for k2, v in zip(keys2, new_values):
                dict_db[k1][k2] = v

        # old_values + new_values
        assert len(key_value_db) == len(keys1) * len(keys2) * 2

        for k1 in keys1:
            for k2, v in zip(keys2, new_values):
                assert dict_db[k1][k2] == v

                key: bytes = _get_final_key(
                    score_address,
                    ContainerTag.DICT, name.encode(),
                    ContainerUtil.encode_key(k1),
                    ContainerUtil.encode_key(k2),
                    use_rlp=True
                )
                assert key_value_db.get(key) == ContainerUtil.encode_value(v)

        for k1 in keys1:
            for k2 in keys2:
                del dict_db[k1][k2]
                assert dict_db[k1][k2] == get_default_value(value_type)

        assert len(key_value_db) == 0

    @pytest.mark.parametrize(
        "prefixes", [
            (),
            (b"prefix0",),
            (b"prefix0", b"prefix1"),
            (b"prefix0", b"prefix1", b"prefix2"),
        ]
    )
    @pytest.mark.parametrize(
        "old_values,new_values", [
            (
                (True, b"hello", 100, "world", Address(AddressPrefix.EOA, os.urandom(20))),
                (False, b"world", 1234, "helloworld", Address(AddressPrefix.CONTRACT, os.urandom(20))),
            )
        ],
    )
    def test_score_db(self, context, key_value_db, prefixes, old_values, new_values):
        context_db = ContextDatabase(key_value_db, is_shared=False)
        score_address = Address(AddressPrefix.CONTRACT, os.urandom(20))
        score_db = IconScoreDatabase(score_address, context_db)
        args = [score_address]

        self._init_context(context, score_address)
        self._set_revision(context, Revision.USE_RLP.value - 1)

        for prefix in prefixes:
            score_db = score_db.get_sub_db(prefix)
            args.append(prefix)

        for i, value in enumerate(old_values):
            key: bytes = f"key{i}".encode()
            encoded_value: bytes = ContainerUtil.encode_value(value)
            score_db.put(key, encoded_value)
            assert score_db.get(key) == encoded_value

            final_key: bytes = _get_final_key(*args, key, use_rlp=False)
            assert key_value_db.get(final_key) == encoded_value

        self._set_revision(context, Revision.USE_RLP.value)

        for i, value in enumerate(old_values):
            key: bytes = f"key{i}".encode()
            encoded_value: bytes = ContainerUtil.encode_value(value)
            assert score_db.get(key) == encoded_value

            final_key: bytes = _get_final_key(*args, key, use_rlp=False)
            assert key_value_db.get(final_key) == encoded_value

        for i, value in enumerate(new_values):
            key: bytes = f"key{i}".encode()
            encoded_value: bytes = ContainerUtil.encode_value(value)
            score_db.put(key, encoded_value)

            assert score_db.get(key) == encoded_value

            final_key: bytes = _get_final_key(*args, key, use_rlp=True)
            assert key_value_db.get(final_key) == encoded_value

            score_db.delete(key)
            assert score_db.get(key) is None
            assert key_value_db.get(final_key) is None
