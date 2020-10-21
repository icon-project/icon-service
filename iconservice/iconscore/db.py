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

from enum import Enum, Flag, auto
from typing import List, Optional, Union

from iconservice.iconscore.context.context import ContextGetter
from iconservice.base.address import Address
from iconservice.base.exception import (
    AccessDeniedException,
    InvalidParamsException,
)
from iconservice.database.db import (
    ContextDatabase,
    DatabaseObserver,
)
from iconservice.utils.rlp import rlp_encode_bytes


class Tag(Enum):
    ARRAY = b"\x00"
    DICT = b"\x01"
    VAR = b"\x02"


class KeyFlag(Flag):
    NONE = 0
    PREFIX = auto()
    ARRAY_LENGTH = auto()
    TAG = auto()


class Key(object):
    def __init__(self, value: bytes, flags: 'KeyFlag' = KeyFlag.NONE):
        self._value = value
        self._flags = flags

    @property
    def value(self) -> bytes:
        return self._value

    @property
    def flags(self) -> 'KeyFlag':
        return self._flags


class PrefixStorage(object):
    def __init__(self, keys: List[Key] = None):
        self._keys = [] if keys is None else [key for key in keys]

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    def append(self, value: bytes, flags: 'KeyFlag' = KeyFlag.NONE):
        if isinstance(value, bytes) and len(value) > 0:
            self._keys.append(Key(value, flags))
        else:
            raise InvalidParamsException(f"Invalid prefix: {value}")

    @property
    def keys(self) -> List[Key]:
        return self._keys

    def get_final_key(self, key: Union[bytes, 'Key'], version: int = 0) -> bytes:
        if isinstance(key, bytes):
            key = Key(key, KeyFlag.NONE)

        if version == 0:
            return self._get_final_key_v0(key)
        else:
            return self._get_final_key_v1(key)

    def _get_final_key_v0(self, key: 'Key') -> bytes:
        keys = []

        if len(self._keys) > 0:
            key0 = self._keys[0]
            if key0.flags == KeyFlag.TAG and key0.value == Tag.DICT.value:
                for i, key in enumerate(self._keys):
                    if i > 0:
                        keys.append(Tag.DICT.value)
                        keys.append(key.value)

        if key.flags == KeyFlag.ARRAY_LENGTH:
            keys.append(b"size")

        return b"|".join(keys)

    def _get_final_key_v1(self, key: 'Key') -> bytes:
        def func():
            for _key in self._keys:
                yield rlp_encode_bytes(_key.value)

            if key.flags != KeyFlag.ARRAY_LENGTH:
                yield rlp_encode_bytes(key.value)

        return b"".join(func())

    def copy(self) -> 'PrefixStorage':
        return PrefixStorage(self._keys)


class ScoreDatabase(ContextGetter):
    """It is used in IconScore

    IconScore can access its states only through IconScoreDatabase
    """

    def __init__(self, address: 'Address', context_db: 'ContextDatabase'):
        """Constructor

        :param address: the address of SCORE which this db is assigned to
        :param context_db: ContextDatabase
        """
        self._address = address
        self._context_db = context_db
        self._observer: Optional[DatabaseObserver] = None

    @property
    def address(self) -> 'Address':
        return self._address

    def __contains__(self, key: bytes) -> bool:
        hashed_key = self._get_final_key(key)
        return self._context_db.get(self._context, hashed_key) is not None

    def get(self, key: bytes) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        hashed_key = self._get_final_key(key)
        value = self._context_db.get(self._context, hashed_key)
        if self._observer:
            self._observer.on_get(self._context, key, value)
        return value

    def put(self, key: bytes, value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        self._validate_ownership()
        hashed_key = self._get_final_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, hashed_key)
            if value:
                self._observer.on_put(self._context, key, old_value, value)
            elif old_value:
                # If new value is None, then deletes the field
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.put(self._context, hashed_key, value)

    # def get_sub_db(self, prefix: bytes) -> 'IconScoreSubDatabase':
    #     """
    #     Returns sub db with a prefix
    #
    #     :param prefix: The prefix used by this sub db.
    #     :return: sub db
    #     """
    #     if prefix is None:
    #         raise InvalidParamsException(
    #             'Invalid params: '
    #             'prefix is None in IconScoreDatabase.get_sub_db()')
    #
    #     if self._prefix is not None:
    #         prefix = b'|'.join((self._prefix, prefix))
    #
    #     return IconScoreSubDatabase(self.address, self, prefix)

    def delete(self, key: bytes):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        self._validate_ownership()
        hashed_key = self._get_final_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, hashed_key)
            # If old value is None, won't fire the callback
            if old_value:
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.delete(self._context, hashed_key)

    def close(self):
        self._context_db.close(self._context)

    def set_observer(self, observer: 'DatabaseObserver'):
        self._observer = observer

    def _get_final_key(self, key: bytes) -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """

        return self._address.to_bytes() + key

    def _validate_ownership(self):
        """Prevent a SCORE from accessing the database of another SCORE

        """
        if self._context.current_address != self.address:
            raise AccessDeniedException("Invalid database ownership")


class PrefixScoreDatabase(object):
    def __init__(
            self,
            score_db: 'ScoreDatabase',
            parent_prefixes: Optional[PrefixStorage],
            prefix: bytes
    ):
        """Constructor

        :param score_db: IconScoreDatabase
        :param parent_prefixes:
        :param prefix:
        """
        self._verify_prefix(prefix)

        self._score_db = score_db

        prefixes = PrefixStorage() if parent_prefixes is None else parent_prefixes.copy()
        prefixes.append(prefix)
        self._prefixes = prefixes

    @property
    def address(self) -> 'Address':
        return self._score_db.address

    @classmethod
    def _verify_prefix(cls, prefix: bytes):
        if not (isinstance(prefix, bytes) and len(prefix) > 0):
            raise InvalidParamsException("Invalid prefix")

    def get(self, key: Union[bytes, 'Key']) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        if isinstance(key, bytes):
            key = Key(key)

        hashed_key = self._hash_key(key)
        return self._score_db.get(hashed_key)

    def put(self, key: Union[bytes, 'Key'], value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        if isinstance(key, bytes):
            key = Key(key)

        hashed_key = self._hash_key(key)
        self._score_db.put(hashed_key, value)

    def get_sub_db(self, prefix: bytes) -> 'PrefixScoreDatabase':
        """
        Returns sub db with a prefix

        :param prefix: The prefix used by this sub db.
        :return: sub db
        """
        return PrefixScoreDatabase(self._score_db, self._prefixes, prefix)

    def delete(self, key: Union[bytes, 'Key']):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        if isinstance(key, bytes):
            key = Key(key)

        hashed_key = self._hash_key(key)
        self._score_db.delete(hashed_key)

    def close(self):
        self._score_db.close()

    def _hash_key(self, key: 'Key') -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """
        return self._prefixes.get_final_key(key)
