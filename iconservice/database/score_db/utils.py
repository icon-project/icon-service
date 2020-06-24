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

from typing import TypeVar

from iconservice import Address

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)

ARRAY_DB_ID = b'\x00'
DICT_DB_ID = b'\x01'
VAR_DB_ID = b'\x02'


class KeyElement:
    def __init__(
            self,
            key: bytes,
            legacy_key: bytes = None,
            is_append_container_id: bool = False
    ):
        """

        :param key:
        :param legacy_key: for arrayDB size branch logic
        :param is_append_container_id: for dictDB depth bug
        """

        self._key: bytes = key
        self._is_append_container_id: bool = is_append_container_id

        if legacy_key:
            self._legacy_key: bytes = legacy_key
        else:
            self._legacy_key: bytes = key

    def __bytes__(self) -> bytes:
        return self.rlp_encode_bytes(self._key)

    @property
    def legacy_key(self) -> bytes:
        return self._legacy_key

    @property
    def is_append_container_id(self) -> bool:
        return self._is_append_container_id

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
