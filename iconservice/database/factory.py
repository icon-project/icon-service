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


import os
from enum import IntEnum

from .db import KeyValueDatabase, ContextDatabase
from ..base.address import Address
from ..icon_constant import ICON_DEX_DB_NAME


class ContextDatabaseFactory(object):

    class Mode(IntEnum):
        SINGLE_DB = 0
        MULTIPLE_DB = 1

    _state_db_root_path: str = None
    _mode: 'Mode' = Mode.SINGLE_DB
    _shared_context_db: 'ContextDatabase' = None

    @classmethod
    def open(cls, state_db_root_path: str, mode: 'Mode'):
        cls.close()

        cls._state_db_root_path = state_db_root_path
        cls._mode = mode

    @classmethod
    def get_shared_db(cls) -> ContextDatabase:
        if cls._shared_context_db is None:
            path = os.path.join(cls._state_db_root_path, ICON_DEX_DB_NAME)
            key_value_db = KeyValueDatabase.from_path(path)
            cls._shared_context_db = ContextDatabase(
                key_value_db, is_shared=True)

        return cls._shared_context_db

    @classmethod
    def create_by_address(cls, address: 'Address') -> ContextDatabase:
        if cls._mode == cls.Mode.SINGLE_DB:
            return cls.get_shared_db()
        else:
            return cls.create_by_name(address.body.hex())

    @classmethod
    def create_by_name(cls, name: str) -> ContextDatabase:
        if cls._mode == cls.Mode.SINGLE_DB:
            return cls.get_shared_db()
        else:
            path = os.path.join(cls._state_db_root_path, name)
            return ContextDatabase.from_path(path)

    @classmethod
    def close(cls):
        if cls._shared_context_db:
            cls._shared_context_db.key_value_db.close()
            cls._shared_context_db = None
