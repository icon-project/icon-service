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

from __future__ import annotations

from enum import Enum, auto
from typing import Union, Iterable, Iterator, Optional, Tuple, List

from .context.context import ContextGetter
from ..base.address import Address
from ..base.exception import (
    AccessDeniedException,
)
from ..database.db import (
    ContextDatabase,
    DatabaseObserver,
)
from ..icon_constant import Revision
from ..utils import bytes_to_hex
from ..utils.rlp import rlp_encode_bytes


class ContainerTag(Enum):
    """Container Type used in SCORE
    """
    ARRAY = b"\x00"
    DICT = b"\x01"
    VAR = b"\x02"


class KeyType(Enum):
    ARRAY = auto()
    DICT = auto()
    VAR = auto()
    SUB = auto()

    ARRAY_SIZE = auto()
    DUMMY = auto()
    LAST = auto()


class Key(object):
    def __init__(self, value: bytes, _type: KeyType = KeyType.LAST):
        self._value = value
        self._type = _type

    @property
    def value(self) -> bytes:
        return self._value

    @property
    def type(self) -> KeyType:
        return self._type

    def __str__(self):
        return f"Key(value={bytes_to_hex(self._value)}, type={self._type.name})"


def verify_single_prefix(prefix: Union[bytes, Key]) -> bool:
    if isinstance(prefix, Key):
        return True

    if isinstance(prefix, bytes) and len(prefix) > 0:
        return True

    return False


def _to_key(key: Union[bytes, Key]) -> Key:
    return Key(key) if isinstance(key, bytes) else key


def to_tag(key_type: KeyType) -> Optional[ContainerTag]:
    if KeyType.ARRAY == key_type:
        return ContainerTag.ARRAY
    elif KeyType.DICT == key_type:
        return ContainerTag.DICT
    elif KeyType.VAR == key_type:
        return ContainerTag.VAR

    return None


def _is_container_name(key: Key) -> bool:
    return key.type in {KeyType.ARRAY, KeyType.DICT, KeyType.VAR}


def to_key_body(address: Address, final_key: bytes, use_rlp: bool) -> bytes:
    """Returns the rest of a given final key excluding score_address prefix

    :param address:
    :param final_key:
    :param use_rlp:
    :return:
    """
    prefix_size = len(address.to_bytes())
    if not use_rlp:
        # Additionally remove b"|" from final_key
        prefix_size += 1

    return final_key[prefix_size:]


class PrefixStorage(object):
    """Stores multiple prefixes

    Prefix keys are some parts of final key which is used for querying stateDB

    """
    def __init__(self, keys: Iterator[Key] = None):
        self._tag: Optional[ContainerTag] = None
        self._keys = [] if keys is None else [key for key in keys]

        if len(self._keys) > 0:
            key = self._keys[-1]
            if _is_container_name(key):
                self._tag = to_tag(key.type)

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    def append(self, key: Union[bytes, Key]):
        key = _to_key(key)

        if _is_container_name(key):
            self._tag = to_tag(key.type)

        self._keys.append(key)

    def get_final_key(self, key: Union[bytes, Key], use_rlp: bool) -> bytes:
        key: Key = _to_key(key)

        if use_rlp:
            return self._get_final_key_with_rlp(key)
        else:
            return self._get_final_key_with_pipe(key)

    def _get_final_key_with_pipe(self, last_key: Key) -> bytes:
        """Generate a final key with '|' separator

        :param last_key:
        :return:
        """
        if isinstance(self._tag, ContainerTag):
            keys: List[bytes] = self._get_container_final_key_with_pipe(last_key)
        else:
            keys: List[bytes] = [key.value for key in self._keys]
            keys.append(last_key.value)

        return b"|".join(keys)

    def _get_container_final_key_with_pipe(self, last_key: Key) -> List[bytes]:
        keys = []

        for key in self._keys:
            if key.type in (KeyType.ARRAY, KeyType.DICT, KeyType.VAR):
                keys.append(self._tag.value)
            keys.append(key.value)

        if last_key.type != KeyType.DUMMY:
            keys.append(last_key.value)

        return keys

    def _get_final_key_with_rlp(self, last_key: Key) -> bytes:
        """Generate final key with rlp

        :param last_key:
        :return:
        """
        def func():
            if isinstance(self._tag, ContainerTag):
                yield self._tag.value

            for _key in self._keys:
                yield rlp_encode_bytes(_key.value)

            if last_key.type != KeyType.ARRAY_SIZE and len(last_key.value) > 0:
                yield rlp_encode_bytes(last_key.value)

        return b"".join(func())

    def copy(self) -> PrefixStorage:
        return PrefixStorage(self._keys)


class KeyValuePair:
    def __init__(self, key: Optional[bytes], value: Optional[bytes], use_rlp: bool = False):
        self._key = key
        self._value = value
        self._use_rlp = use_rlp

    @property
    def key(self) -> Optional[bytes]:
        return self._key

    @property
    def value(self) -> Optional[bytes]:
        return self._value

    @property
    def use_rlp(self) -> bool:
        return self._use_rlp


class IconScoreDatabase(ContextGetter):
    """It is used in IconScore

    IconScore can access its states only through IconScoreDatabase
    """

    def __init__(
            self,
            address: 'Address',
            context_db: 'ContextDatabase',
            prev_prefixes: Iterable[Key] = None,
            prefix: Union[bytes, Key] = None,
            origin_score_db: Optional[IconScoreDatabase] = None,
    ):
        """Constructor

        :param address: the address of SCORE which this db is assigned to
        :param context_db: ContextDatabase
        """
        self._address = address
        self._context_db = context_db
        self._observer: Optional[DatabaseObserver] = None
        self._origin_score_db = origin_score_db

        self._prefixes = PrefixStorage(prev_prefixes)
        if prefix:
            self._prefixes.append(prefix)

    @property
    def address(self) -> Address:
        return self._address

    def _use_rlp(self) -> bool:
        return self._context.revision >= Revision.USE_RLP.value

    def _context_db_get(self, key: bytes) -> Optional[bytes]:
        return self._context_db.get(self._context, key)

    def _context_db_put(self, key: bytes, value: bytes):
        self._context_db.put(self._context, key, value)

    def _context_db_delete(self, key: Optional[bytes]):
        if key:
            self._context_db.delete(self._context, key)

    def get(self, key: Union[bytes, Key]) -> bytes:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        key = _to_key(key)

        old_kv_pair, new_kv_pair = self._get(key)
        final_key: bytes = new_kv_pair.key if new_kv_pair.key else old_kv_pair.key
        value: bytes = new_kv_pair.value if new_kv_pair.value else old_kv_pair.value

        observer = self.__get_observer()
        if observer:
            observer.on_get(self._context, self._to_key_body(final_key), value)

        return value

    def _get(
            self,
            key: Union[bytes, Key]
    ) -> Tuple[KeyValuePair, KeyValuePair]:
        old_value, new_value = None, None
        old_final_key = self._get_final_key(key, use_rlp=False)
        new_final_key = None

        if self._use_rlp():
            new_final_key = self._get_final_key(key, use_rlp=True)
            new_value: Optional[bytes] = self._context_db_get(new_final_key)

        if new_value is None:
            old_value: Optional[bytes] = self._context_db_get(old_final_key)

        return (
            KeyValuePair(old_final_key, old_value, use_rlp=False),
            KeyValuePair(new_final_key, new_value, use_rlp=True),
        )

    def put(self, key: Union[bytes, Key], value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        self._validate_ownership()

        old_kv_pair, new_kv_pair = self._get(key)
        final_key: bytes = new_kv_pair.key if new_kv_pair.key else old_kv_pair.key
        prev_value: bytes = new_kv_pair.value if new_kv_pair.value else old_kv_pair.value

        observer = self.__get_observer()
        if observer:
            key_body: bytes = self._to_key_body(final_key)
            if value:
                observer.on_put(self._context, key_body, prev_value, value)
            elif prev_value:
                # If new value is None, then deletes the field
                observer.on_delete(self._context, key_body, prev_value)

        self._context_db.put(self._context, final_key, value)

    def get_sub_db(self, prefix: Union[bytes, Key]) -> IconScoreDatabase:
        """
        Returns sub db with a prefix

        :param prefix: The prefix used by this sub db.
        :return: sub db
        """
        origin_score_db = self._origin_score_db if self._origin_score_db else self

        score_db = IconScoreDatabase(
            address=self._address,
            context_db=self._context_db,
            prev_prefixes=self._prefixes,
            prefix=prefix,
            origin_score_db=origin_score_db
        )
        score_db.set_observer(self._observer)

        return score_db

    def delete(self, key: Union[bytes, Key]):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        self._validate_ownership()

        old_kv_pair, new_kv_pair = self._get(key)
        final_key: bytes = new_kv_pair.key if new_kv_pair.key else old_kv_pair.key
        value: bytes = new_kv_pair.value if new_kv_pair.value else old_kv_pair.value

        observer = self.__get_observer()
        if observer:
            if value:
                observer.on_delete(self._context, self._to_key_body(final_key), value)

        self._context_db_delete(old_kv_pair.key)
        self._context_db_delete(new_kv_pair.key)

    def close(self):
        self._context_db.close(self._context)

    def set_observer(self, observer: DatabaseObserver):
        self._observer = observer

    def __get_observer(self) -> Optional[DatabaseObserver]:
        if self._observer:
            return self._observer

        if self._origin_score_db:
            return self._origin_score_db.__get_observer()

        return None

    def _get_final_key(self, key: Union[bytes, Key], use_rlp: bool) -> bytes:
        """
        :params key: key passed by SCORE
        :return: key bytes
        """
        body: bytes = self._prefixes.get_final_key(key, use_rlp)
        sep = b"" if use_rlp else b"|"

        return sep.join((self._address.to_bytes(), body))

    def _validate_ownership(self):
        """Prevent a SCORE from accessing the database of another SCORE

        """
        if self._context.current_address != self.address:
            raise AccessDeniedException("Invalid database ownership")

    def _to_key_body(self, final_key: bytes) -> bytes:
        return to_key_body(self._address, final_key, self._use_rlp())
