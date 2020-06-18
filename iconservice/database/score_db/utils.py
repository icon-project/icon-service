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

from typing import Union, Optional

from iconservice.base.exception import InvalidParamsException
from typing import TypeVar

from iconservice import Address

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)

ARRAY_DB_ID = b'\x00'
DICT_DB_ID = b'\x01'
VAR_DB_ID = b'\x02'


def make_rlp_prefix_list(
        prefix: bytes,
        legacy_key: bytes = None,
        prefix_container_id: bool = False
) -> list:
    return [
        RLPPrefix(
            prefix=prefix,
            legacy_key=legacy_key,
            prefix_container_id=prefix_container_id
        )
    ]


class RLPPrefix:
    def __init__(
            self,
            prefix: bytes,
            legacy_key: bytes = None,
            prefix_container_id: bool = False
    ):
        self._prefix: bytes = prefix
        self._prefix_container_id: bool = prefix_container_id

        if legacy_key:
            self._legacy_key: bytes = legacy_key
        else:
            self._legacy_key: bytes = prefix

    def __bytes__(self) -> bytes:
        return self.rlp_encode_bytes(self._prefix)

    @property
    def legacy_key(self) -> bytes:
        return self._legacy_key

    @property
    def prefix_container_id(self) -> bool:
        return self._prefix_container_id

    @classmethod
    def rlp_encode_bytes(cls, b: bytes) -> bytes:
        blen = len(b)
        if blen == 1 and b[0] < 0x80:
            return b
        elif blen <= 55:
            return bytes([blen + 0x80]) + b
        len_bytes = cls.rlp_get_bytes(blen)
        return bytes([len(len_bytes) + 0x80 + 55]) + len_bytes + b

    @classmethod
    def rlp_get_bytes(cls, x: int) -> bytes:
        if x == 0:
            return b''
        else:
            return cls.rlp_get_bytes(int(x / 256)) + bytes([x % 256])
