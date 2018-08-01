# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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


"""iconservice unittest package
"""


import hashlib
import shutil
import sys

import time
import random
from typing import TYPE_CHECKING

from iconservice.base.address import Address
from iconservice.icon_constant import DATA_BYTE_ORDER

if TYPE_CHECKING:
    from iconservice.base.address import AddressPrefix


def create_address(prefix: 'AddressPrefix', data: bytes) -> 'Address':
    hash_value = hashlib.sha3_256(data).digest()
    return Address(prefix, hash_value[-20:])


def create_hash_256(data: bytes=None) -> bytes:
    if data is None:
        max_int = sys.maxsize
        length = (max_int.bit_length() + 7) // 8
        data = int(random.randint(0, max_int)).to_bytes(length, DATA_BYTE_ORDER)

    return hashlib.sha3_256(data).digest()


def create_tx_hash(data: bytes=None) -> bytes:
    return create_hash_256(data)


def create_block_hash(data: bytes=None) -> bytes:
    return create_tx_hash(data)


def rmtree(path: str) -> None:
    try:
        shutil.rmtree(path)
    except Exception as e:
        pass
