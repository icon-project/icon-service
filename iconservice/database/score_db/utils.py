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

import enum
from typing import TypeVar, List, Optional

from iconservice import Address
from iconservice.utils import set_flag, is_any_flag_on, is_all_flag_on

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)

ARRAY_DB_ID = b'\x00'
DICT_DB_ID = b'\x01'
VAR_DB_ID = b'\x02'


class KeyElementState(enum.Flag):
    NONE = 0
    IS_CONSTRUCTOR = 1
    IS_CONTAINER = 2
    IS_PREFIX = 4


class KeyElement:
    def __init__(
            self,
            keys: List[bytes],
            tag: Optional[bytes],
            state: 'KeyElementState' = KeyElementState.NONE
    ):
        """

        :param keys: contain with legacy key
        :param tag:
        :param state:
        """

        self._keys: List[bytes] = keys
        self._tag: Optional[bytes] = tag
        self._state: 'KeyElementState' = state

    @property
    def tag(self) -> bytes:
        return self._tag

    @property
    def is_prefix(self) -> bool:
        return is_any_flag_on(
            src_flags=self._state,
            flag=KeyElementState.IS_PREFIX,
        )

    def to_bytes(self, is_legacy: bool) -> bytes:
        if is_legacy:
            if is_all_flag_on(self._state, KeyElementState.IS_CONSTRUCTOR | KeyElementState.IS_CONTAINER):
                # 1. Bug DictDB (is appended container_id whenever make sub db in DictDB)
                return b'|'.join((self._tag, self._keys[0]))
            elif self._tag == ARRAY_DB_ID and len(self._keys) == 2:
                # 2. Consider array size key
                return self._keys[1]
            else:
                return self._keys[0]
        else:
            return self._rlp_encode_bytes(self._keys[0])

    def enable_is_prefix(self, on: bool):
        self._state = set_flag(
            src_flags=self._state,
            flag=KeyElementState.IS_PREFIX,
            on=on,
        )

    @classmethod
    def _rlp_encode_bytes(cls, b: bytes) -> bytes:
        blen = len(b)
        if blen == 1 and b[0] < 0x80:
            return b
        elif blen <= 55:
            return bytes([blen + 0x80]) + b
        len_bytes = cls._rlp_get_bytes(blen)
        return bytes([len(len_bytes) + 0x80 + 55]) + len_bytes + b

    @classmethod
    def _rlp_get_bytes(cls, x: int) -> bytes:
        if x == 0:
            return b''
        else:
            return cls._rlp_get_bytes(int(x / 256)) + bytes([x % 256])
