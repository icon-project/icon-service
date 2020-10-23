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
from typing import Union, Iterator, Optional

from .context.context import ContextGetter
from ..base.address import Address
from ..base.exception import (
    AccessDeniedException,
    InvalidParamsException,
)
from ..database.db import (
    ContextDatabase,
    DatabaseObserver,
)
from ..icon_constant import Revision
from ..utils import bytes_to_hex
from ..utils.rlp import rlp_encode_bytes


def verify_prefix(prefix: Union[bytes, 'Key']):
    if isinstance(prefix, Key):
        return

    if not (isinstance(prefix, bytes) and len(prefix) > 0):
        raise InvalidParamsException("Invalid prefix")


def _to_key(key: Union[bytes, 'Key']) -> 'Key':
    if isinstance(key, bytes):
        key = Key(key, KeyFlag.NONE)

    return key


class Tag(Enum):
    ARRAY = b"\x00"
    DICT = b"\x01"
    VAR = b"\x02"


class KeyFlag(Flag):
    NONE = 0
    ARRAY_LENGTH = auto()
    TAG = auto()

    # Use | separator
    PIPE = auto()


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

    def __str__(self):
        return f"Key(value={bytes_to_hex(self._value)}, flags={self._flags})"


class PrefixStorage(object):
    """Stores multiple prefix keys

    Prefix keys are some parts of final key which is used for querying stateDB

    """
    def __init__(self, keys: Iterator[Key] = None):
        self._keys = [] if keys is None else [key for key in keys]

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    def append(self, key: Union[bytes, 'Key']):
        key = _to_key(key)

        if key.flags == KeyFlag.TAG and len(self._keys) > 0:
            # Block to append additional tags
            return

        self._keys.append(key)

    def get_final_key(self, key: Union[bytes, 'Key'], use_rlp: bool) -> bytes:
        key = _to_key(key)

        if use_rlp:
            return self._get_final_key_v1(key)
        else:
            return self._get_final_key_v0(key)

    def _get_final_key_v0(self, last_key: 'Key') -> bytes:
        """Generate a final key with '|' separator

        :param last_key:
        :return:
        """
        keys = []

        if len(self._keys) > 0:
            key0 = self._keys[0]  # Tag key

            if key0.flags == KeyFlag.TAG and key0.value == Tag.DICT.value:
                for i, key in enumerate(self._keys):
                    if i > 0:
                        keys.append(key0.value)  # Tag key
                        keys.append(key.value)
            else:
                for key in self._keys:
                    keys.append(key.value)

        keys.append(last_key.value)

        return b"|".join(keys)

    def _get_final_key_v1(self, last_key: 'Key') -> bytes:
        """Generate final key with rlp

        :param last_key:
        :return:
        """
        def func():
            for _key in self._keys:
                yield rlp_encode_bytes(_key.value)

            if last_key.flags != KeyFlag.ARRAY_LENGTH:
                yield rlp_encode_bytes(last_key.value)

        return b"".join(func())

    def copy(self) -> 'PrefixStorage':
        return PrefixStorage(self._keys)


class IconScoreDatabase(ContextGetter):
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
        final_key: bytes = self._get_final_key(key)
        return self._context_db.get(self._context, final_key) is not None

    def get(self, key: Union[bytes, 'Key']) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        final_key: bytes = self._get_final_key(key)
        value = self._context_db.get(self._context, final_key)
        if self._observer:
            self._observer.on_get(self._context, key, value)
        return value

    def put(self, key: Union[bytes, 'Key'], value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        self._validate_ownership()
        final_key: bytes = self._get_final_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, final_key)
            if value:
                self._observer.on_put(self._context, key, old_value, value)
            elif old_value:
                # If new value is None, then deletes the field
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.put(self._context, final_key, value)

    def get_sub_db(self, prefix: Union[bytes, 'Key']) -> 'PrefixScoreDatabase':
        """
        Returns sub db with a prefix

        :param prefix: The prefix used by this sub db.
        :return: sub db
        """
        return PrefixScoreDatabase(self, parent_prefixes=None, prefix=prefix)

    def delete(self, key: Union[bytes, 'Key']):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        self._validate_ownership()
        final_key: bytes = self._get_final_key(key)
        if self._observer:
            old_value = self._context_db.get(self._context, final_key)
            # If old value is None, won't fire the callback
            if old_value:
                self._observer.on_delete(self._context, key, old_value)
        self._context_db.delete(self._context, final_key)

    def close(self):
        self._context_db.close(self._context)

    def set_observer(self, observer: 'DatabaseObserver'):
        self._observer = observer

    def _get_final_key(self, key: Union[bytes, 'Key']) -> bytes:
        """
        :params key: key passed by SCORE
        :return: key bytes
        """
        key = _to_key(key)

        if self._use_rlp():
            separator = b"|" if KeyFlag.PIPE in key.flags else b""
        else:
            separator = b"|"

        return b"".join((self._address.to_bytes(), separator, key.value))

    def _validate_ownership(self):
        """Prevent a SCORE from accessing the database of another SCORE

        """
        if self._context.current_address != self.address:
            raise AccessDeniedException("Invalid database ownership")

    def _use_rlp(self) -> bool:
        return self._context.revision >= Revision.USE_RLP.value


class PrefixScoreDatabase(ContextGetter):
    def __init__(
            self,
            score_db: 'IconScoreDatabase',
            parent_prefixes: Optional[PrefixStorage],
            prefix: Union[bytes, 'Key']
    ):
        """Constructor

        :param score_db: IconScoreDatabase
        :param parent_prefixes:
        :param prefix:
        """
        verify_prefix(prefix)

        self._score_db = score_db

        prefixes = PrefixStorage() if parent_prefixes is None else parent_prefixes.copy()
        prefixes.append(prefix)
        self._prefixes = prefixes

    @property
    def address(self) -> 'Address':
        return self._score_db.address

    @property
    def prefixes(self) -> 'PrefixStorage':
        return self._prefixes

    def _use_rlp(self) -> bool:
        return self._context.revision >= Revision.USE_RLP.value

    def get(self, key: Union[bytes, 'Key']) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        if self._use_rlp():
            final_key: 'Key' = self._generate_final_key(key, use_rlp=True)
            value: Optional[bytes] = self._score_db.get(final_key)
            if isinstance(value, bytes):
                return value

        final_key = self._generate_final_key(key, use_rlp=False)
        return self._score_db.get(final_key)

    def put(self, key: Union[bytes, 'Key'], value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        final_key: 'Key' = self._generate_final_key(key, use_rlp=self._use_rlp())
        self._score_db.put(final_key, value)

    def get_sub_db(self, prefix: Union[bytes, 'Key']) -> 'PrefixScoreDatabase':
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
        if self._use_rlp():
            final_key: 'Key' = self._generate_final_key(key, use_rlp=True)
            self._score_db.delete(final_key)

        final_key: 'Key' = self._generate_final_key(key, use_rlp=False)
        self._score_db.delete(final_key)

    def close(self):
        self._score_db.close()

    def _generate_final_key(self, key: Union[bytes, 'Key'], use_rlp: bool) -> Key:
        """
        :params key: key passed by SCORE
        :params use_rlp: whether to use rtp when generating final key
        :return: key bytes
        """
        value: bytes = self._prefixes.get_final_key(_to_key(key), use_rlp)
        return Key(value, KeyFlag.NONE if use_rlp else KeyFlag.PIPE)
