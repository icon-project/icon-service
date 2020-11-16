from typing import Union

import pytest

from iconservice.iconscore.db import (
    Key,
    KeyType,
    PrefixStorage,
    ContainerTag,
    to_tag,
)
from iconservice.utils import int_to_bytes
from iconservice.utils.rlp import rlp_encode_bytes


def _to_bytes(key: Union[bytes, Key, ContainerTag]) -> bytes:
    if isinstance(key, (ContainerTag, Key)):
        return key.value
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
    return b"".join((rlp_encode_bytes(key) for key in args))


class TestPrefixStorage:
    def test_get_final_key(self):
        keys = Key(b"balances", KeyType.ARRAY),
        prefixes = PrefixStorage(keys)
        for key, expected in zip(prefixes, keys):
            assert key is expected

        # Length of ArrayDB whose name is b"balances" in version 0
        last_key = Key(b"size", KeyType.ARRAY_SIZE)
        final_key: bytes = prefixes.get_final_key(last_key, use_rlp=False)
        assert final_key == _get_final_key(ContainerTag.ARRAY.value, keys[0].value, last_key.value, use_rlp=False)

        # Length of ArrayDB whose name is b"balances" in version 1
        final_key: bytes = prefixes.get_final_key(last_key, use_rlp=True)
        assert final_key == _get_final_key(ContainerTag.ARRAY.value, keys[0].value, use_rlp=True)

    def test_get_final_key_2(self):
        keys = (
            Key(b"prefix0"),
            Key(b"prefix1"),
            Key(b"dict1", KeyType.DICT),
        )
        prefixes = PrefixStorage(keys)
        assert prefixes._tag == ContainerTag.DICT
        assert len(prefixes) == len(keys)
        for key, expected in zip(prefixes, keys):
            assert key is expected

        last_key = b"last"

        final_key: bytes = prefixes.get_final_key(last_key, use_rlp=False)
        assert final_key == _get_final_key(*keys[:2], ContainerTag.DICT, keys[2], last_key, use_rlp=False)

        final_key: bytes = prefixes.get_final_key(last_key, True)
        assert final_key == _get_final_key(ContainerTag.DICT, *keys, last_key, use_rlp=True)

    def test_get_final_key_3(self):
        keys = (
            Key(b"prefix"),
            Key(b"dict1", KeyType.DICT),
            Key(b"dict2", KeyType.DICT),
            Key(b"dict3", KeyType.DICT),
        )
        prefixes = PrefixStorage(keys)
        assert prefixes._tag == ContainerTag.DICT
        assert len(prefixes) == len(keys)
        for key, expected in zip(prefixes, keys):
            assert key is expected

        last_key = b"last"

        final_key: bytes = prefixes.get_final_key(last_key, use_rlp=False)
        assert final_key == _get_final_key(
            keys[0],
            ContainerTag.DICT, keys[1],
            ContainerTag.DICT, keys[2],
            ContainerTag.DICT, keys[3],
            last_key,
            use_rlp=False
        )

        final_key: bytes = prefixes.get_final_key(last_key, True)
        assert final_key == _get_final_key(ContainerTag.DICT, *keys, last_key, use_rlp=True)

    @pytest.mark.parametrize(
        "size", [i for i in range(3)]
    )
    def test_get_final_key_4(self, size):
        keys = [Key(f"prefix{i}".encode()) for i in range(size)]
        prefixes = PrefixStorage(keys)
        assert prefixes._tag is None
        assert len(prefixes) == size
        for key, expected in zip(prefixes, keys):
            assert key is expected

        name = Key(b"array", KeyType.ARRAY)
        prefixes.append(name)
        assert prefixes._tag is ContainerTag.ARRAY
        assert len(prefixes) == size + 1

        last_key = int_to_bytes(0)

        final_key: bytes = prefixes.get_final_key(last_key, use_rlp=False)
        assert final_key == _get_final_key(*keys[:size], ContainerTag.ARRAY, name, last_key, use_rlp=False)

        final_key: bytes = prefixes.get_final_key(last_key, True)
        assert final_key == _get_final_key(ContainerTag.ARRAY, *prefixes, last_key, use_rlp=True)

    def test_append(self):
        prefixes = PrefixStorage()
        assert len(prefixes) == 0
        assert prefixes._tag is None

        size = 10
        for i in range(size):
            prefixes.append(f"prefix{i}".encode())
            assert len(prefixes) == i + 1
            assert prefixes._tag is None

        for i, prefix in enumerate(prefixes):
            assert isinstance(prefix, Key)
            assert prefix.value == f"prefix{i}".encode()

        for key_type in (KeyType.ARRAY, KeyType.DICT, KeyType.VAR):
            new_prefixes = PrefixStorage(iter(prefixes))
            assert len(new_prefixes) == size
            assert prefixes._tag is None

            key = Key(b"name", key_type)
            new_prefixes.append(key)
            assert len(new_prefixes) == size + 1
            assert new_prefixes._tag == to_tag(key_type)
