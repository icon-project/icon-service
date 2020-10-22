from typing import Iterator

import pytest

from iconservice.iconscore.db import (
    Key,
    KeyFlag,
    PrefixStorage,
    Tag,
)
from iconservice.utils.rlp import rlp_encode_bytes
from iconservice.utils import int_to_bytes


def concatenate_rlp_encoded_keys(keys: Iterator[bytes]) -> bytes:
    return b"".join((rlp_encode_bytes(key) for key in keys))


class TestPrefixStorage:
    def test_get_final_key(self):
        keys = (
            Key(Tag.ARRAY.value, KeyFlag.TAG),
            Key(b"balances"),
        )
        prefixes = PrefixStorage(keys)
        for key, expected in zip(prefixes, keys):
            assert key is expected

        # Length of ArrayDB whose name is b"balances" in version 0
        last_key = Key(b"size", KeyFlag.ARRAY_LENGTH)
        final_key: bytes = prefixes.get_final_key(last_key, version=0)
        assert final_key == b"|".join((key.value for key in keys)) + b"|" + last_key.value

        # Length of ArrayDB whose name is b"balances" in version 1
        final_key: bytes = prefixes.get_final_key(last_key, version=1)
        assert final_key == concatenate_rlp_encoded_keys((key.value for key in keys))

    def test_get_final_key_2(self):
        keys = [
            Key(Tag.DICT.value, KeyFlag.TAG),
            Key(b"key0"),
            Key(b"key1"),
        ]
        prefixes = PrefixStorage(keys)
        for key, expected in zip(prefixes, keys):
            assert key is expected

        last_key = Key(b"last_key")

        final_key: bytes = prefixes.get_final_key(last_key, version=0)

        def func_v0():
            for i, _key in enumerate(keys):
                if i > 0:
                    yield keys[0].value
                    yield _key.value

            yield last_key.value
        assert final_key == b"|".join(func_v0())

        final_key: bytes = prefixes.get_final_key(last_key, version=1)
        assert final_key == concatenate_rlp_encoded_keys(
            [key.value for key in keys] + [last_key.value]
        )

    def test_append(self):
        prefixes = PrefixStorage()
        assert len(prefixes) == 0

        tag = Key(Tag.ARRAY.value, KeyFlag.TAG)
        for _ in range(10):
            prefixes.append(tag)
            assert len(prefixes) == 1

        size = 10
        for i in range(size):
            value = int_to_bytes(i)
            prefixes.append(value)

        assert len(prefixes) == size + 1
