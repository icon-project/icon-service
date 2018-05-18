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


import hashlib
from enum import IntEnum

from ..base.address import Address, AddressPrefix


def create_address(prefix: AddressPrefix, data: bytes):
    hash_value = hashlib.sha3_256(data).digest()
    return Address(prefix, hash_value[-20:])


class OnInitType(IntEnum):
    """Value used to call IconScoreBase.on_init()
    """
    NONE = -1
    INSTALL = 0
    UPDATE = 1

    @staticmethod
    def from_data_type(data_type: str):
        if data_type == 'install':
            return OnInitType.INSTALL
        elif data_type == 'update':
            return OnInitType.UPDATE
        return OnInitType.NONE
