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

from typing import TypeVar, Optional, Any, Union

from .context.context import ContextContainer
from .db import IconScoreDatabase, Key, KeyType
from ..base.address import Address
from ..base.exception import InvalidParamsException, InvalidContainerAccessException
from ..icon_constant import IconScoreContextType, Revision
from ..utils import int_to_bytes, bytes_to_int

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)


def get_encoded_key(key: V) -> bytes:
    return ContainerUtil.encode_key(key)


class ContainerUtil(object):

    @classmethod
    def encode_key(cls, key: K) -> bytes:
        """Create a key passed to IconScoreDatabase

        :param key:
        :return:
        """
        if key is None:
            raise InvalidParamsException('key is None')

        if isinstance(key, int):
            bytes_key = int_to_bytes(key)
        elif isinstance(key, str):
            bytes_key = key.encode('utf-8')
        elif isinstance(key, Address):
            bytes_key = key.to_bytes()
        elif isinstance(key, bytes):
            bytes_key = key
        else:
            raise InvalidParamsException(f'Unsupported key type: {type(key)}')
        return bytes_key

    @classmethod
    def encode_value(cls, value: V) -> bytes:
        if isinstance(value, int):
            byte_value = int_to_bytes(value)
        elif isinstance(value, str):
            byte_value = value.encode('utf-8')
        elif isinstance(value, Address):
            byte_value = value.to_bytes()
        elif isinstance(value, bool):
            byte_value = int_to_bytes(int(value))
        elif isinstance(value, bytes):
            byte_value = value
        else:
            raise InvalidParamsException(f'Unsupported value type: {type(value)}')
        return byte_value

    @classmethod
    def decode_object(cls, value: bytes, value_type: type) -> Optional[Union[K, V]]:
        if value is None:
            return get_default_value(value_type)

        obj_value = None
        if value_type == int:
            obj_value = bytes_to_int(value)
        elif value_type == str:
            obj_value = value.decode()
        elif value_type == Address:
            obj_value = Address.from_bytes(value)
        if value_type == bool:
            obj_value = bool(bytes_to_int(value))
        elif value_type == bytes:
            obj_value = value
        return obj_value


class DictDB(object):
    """
    Utility classes wrapping the state DB.
    DictDB behaves more like python dict.
    DictDB does not maintain order.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """

    def __init__(self,
                 var_key: K,
                 db: IconScoreDatabase,
                 value_type: type,
                 depth: int = 1) -> None:
        if not (1 <= depth <= 5):
            raise InvalidParamsException(f"Depth out of range: {depth}")

        self._db = db.get_sub_db(Key(get_encoded_key(var_key), KeyType.DICT))
        self.__value_type = value_type
        self.__depth = depth

    def remove(self, key: K) -> None:
        """
        Removes the value of given key

        :param key:
        """
        if self.__depth != 1:
            raise InvalidContainerAccessException('DictDB depth mismatch')
        self._db.delete(get_encoded_key(key))

    def __setitem__(self, key: K, value: V) -> None:
        if self.__depth != 1:
            raise InvalidContainerAccessException('DictDB depth mismatch')

        encoded_key: bytes = get_encoded_key(key)
        encoded_value: bytes = ContainerUtil.encode_value(value)

        self._db.put(encoded_key, encoded_value)

    def __getitem__(self, key: K) -> Any:
        if self.__depth == 1:
            encoded_key: bytes = get_encoded_key(key)
            return ContainerUtil.decode_object(self._db.get(encoded_key), self.__value_type)
        else:
            return DictDB(key, self._db, self.__value_type, self.__depth - 1)

    def __delitem__(self, key: K):
        self.remove(key)

    def __contains__(self, key: K):
        # Plyvel doesn't allow setting None value in the DB.
        # so there is no case of returning None value if the key exists.
        value = self._db.get(get_encoded_key(key))
        return value is not None

    def __iter__(self):
        raise InvalidContainerAccessException("Iteration not supported in DictDB")


class ArrayDB(object):
    """
    Utility classes wrapping the state DB.
    ArrayDB supports length and iterator, maintains order.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """
    SIZE_BYTE_KEY = b"size"

    def __init__(self, var_key: K, db: 'IconScoreDatabase', value_type: type) -> None:
        self._db: IconScoreDatabase = db.get_sub_db(Key(get_encoded_key(var_key), KeyType.ARRAY))

        self.__value_type = value_type
        self.__legacy_size = self.__get_size_from_db()

    def put(self, value: V) -> None:
        """
        Puts the value at the end of array

        :param value: value to add
        """
        size: int = self.__get_size()
        self.__put(size, value)
        self.__set_size(size + 1)

    def pop(self) -> Optional[V]:
        """
        Gets and removes last added value

        :return: last added value
        """
        size: int = self.__get_size()
        if size == 0:
            return None

        index = size - 1
        last_val = self[index]
        self._db.delete(get_encoded_key(index))
        self.__set_size(index)
        return last_val

    def get(self, index: int = 0) -> V:
        """
        Gets the value at index

        :param index: index
        :return: value at the index
        """
        return self.__getitem__(index)

    def __get_size(self) -> int:
        if self.__is_defective_revision():
            return self.__legacy_size
        else:
            return self.__get_size_from_db()

    def __get_size_from_db(self) -> int:
        value: bytes = self._db.get(Key(self.SIZE_BYTE_KEY, KeyType.ARRAY_SIZE))
        return ContainerUtil.decode_object(value, int)

    def __set_size(self, size: int) -> None:
        self.__legacy_size = size
        byte_value = ContainerUtil.encode_value(size)

        key = Key(self.SIZE_BYTE_KEY, KeyType.ARRAY_SIZE)
        self._db.put(key, byte_value)

    def __put(self, index: int, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(get_encoded_key(index), byte_value)

    def __iter__(self):
        size: int = self.__get_size()

        for i in range(size):
            key: bytes = get_encoded_key(i)
            value: bytes = self._db.get(key)
            yield ContainerUtil.decode_object(value, self.__value_type)

    def __len__(self):
        return self.__get_size()

    def __setitem__(self, index: int, value: V) -> None:
        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        size: int = self.__get_size()
        index: int = self._to_positive_index(index, size)
        self.__put(index, value)

    def __getitem__(self, index: int) -> V:
        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        size: int = self.__get_size()
        index: int = self._to_positive_index(index, size)

        key: bytes = get_encoded_key(index)
        value: bytes = self._db.get(key)
        return ContainerUtil.decode_object(value, self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False

    @classmethod
    def __is_defective_revision(cls):
        context = ContextContainer._get_context()
        revision = context.revision
        return context.type == IconScoreContextType.INVOKE and revision < Revision.THREE.value

    @classmethod
    def _to_positive_index(cls, index: int, size: int) -> int:
        if index < 0:
            index += size

        if 0 <= index < size:
            return index

        raise InvalidParamsException('ArrayDB out of index')


class VarDB(object):
    """
    Utility classes wrapping the state DB.
    VarDB can be used to store simple key-value state.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """
    _DUMMY_LAST_KEY = Key(b"", KeyType.DUMMY)

    def __init__(self, var_key: K, db: 'IconScoreDatabase', value_type: type) -> None:
        # Use var_key as a db prefix in the case of VarDB
        self._db = db.get_sub_db(Key(get_encoded_key(var_key), KeyType.VAR))
        self.__value_type = value_type

    def set(self, value: V) -> None:
        """
        Sets the value

        :param value: a value to be set
        """
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(self._DUMMY_LAST_KEY, byte_value)

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        return ContainerUtil.decode_object(
            self._db.get(self._DUMMY_LAST_KEY),
            self.__value_type
        )

    def remove(self) -> None:
        """
        Deletes the value
        """
        self._db.delete(self._DUMMY_LAST_KEY)


def get_default_value(value_type: type) -> Any:
    if value_type == int:
        return 0
    elif value_type == str:
        return ""
    elif value_type == bool:
        return False
    return None
