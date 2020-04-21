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

from typing import TypeVar, Optional, Any, Union, TYPE_CHECKING

from iconservice.icon_constant import IconScoreContextType, Revision
from .context.context import ContextContainer
from ..base.address import Address
from ..base.exception import InvalidParamsException, InvalidContainerAccessException
from ..utils import int_to_bytes, bytes_to_int

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase, IconScoreSubDatabase

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)

ARRAY_DB_ID = b'\x00'
DICT_DB_ID = b'\x01'
VAR_DB_ID = b'\x02'


def get_encoded_key(key: V) -> bytes:
    return ContainerUtil.encode_key(key)


class ContainerUtil(object):

    @classmethod
    def create_db_prefix(cls, container_cls: type, var_key: K) -> bytes:
        """Create a prefix used
        as a parameter of IconScoreDatabase.get_sub_db()

        :param container_cls: ArrayDB, DictDB, VarDB
        :param var_key:
        :return:
        """
        if container_cls == ArrayDB:
            container_id = ARRAY_DB_ID
        elif container_cls == DictDB:
            container_id = DICT_DB_ID
        else:
            raise InvalidParamsException(f'Unsupported container class: {container_cls}')

        encoded_key: bytes = get_encoded_key(var_key)
        return b'|'.join([container_id, encoded_key])

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

    @classmethod
    def remove_prefix_from_iters(cls, iter_items: iter) -> iter:
        return ((cls.__remove_prefix_from_key(key), value) for key, value in iter_items)

    @classmethod
    def __remove_prefix_from_key(cls, key_from_bytes: bytes) -> bytes:
        return key_from_bytes[:-1]

    @classmethod
    def put_to_db(cls, db: 'IconScoreDatabase', db_key: str, container: iter) -> None:
        sub_db = db.get_sub_db(cls.encode_key(db_key))
        if isinstance(container, dict):
            cls.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            cls.__put_to_db_internal(sub_db, enumerate(container))

    @classmethod
    def get_from_db(cls, db: 'IconScoreDatabase', db_key: str, *args, value_type: type) -> Optional[K]:
        sub_db = db.get_sub_db(cls.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(cls.encode_key(arg))

        byte_key = sub_db.get(cls.encode_key(last_arg))
        if byte_key is None:
            return get_default_value(value_type)
        return cls.decode_object(byte_key, value_type)

    @classmethod
    def __put_to_db_internal(cls, db: Union['IconScoreDatabase', 'IconScoreSubDatabase'], iters: iter) -> None:
        for key, value in iters:
            sub_db = db.get_sub_db(cls.encode_key(key))
            if isinstance(value, dict):
                cls.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                cls.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = cls.encode_key(key)
                db_value = cls.encode_value(value)
                db.put(db_key, db_value)


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
                 db: Union['IconScoreDatabase',
                           'IconScoreSubDatabase'],
                 value_type: type,
                 depth: int = 1) -> None:
        prefix: bytes = ContainerUtil.create_db_prefix(type(self), var_key)
        self._db = db.get_sub_db(prefix)

        self.__value_type = value_type
        self.__depth = depth

    def remove(self, key: K) -> None:
        """
        Removes the value of given key

        :param key:
        """
        self.__remove(key)

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
        self.__remove(key)

    def __contains__(self, key: K):
        # Plyvel doesn't allow setting None value in the DB.
        # so there is no case of returning None value if the key exists.
        value = self._db.get(get_encoded_key(key))
        return value is not None

    def __remove(self, key: K) -> None:
        if self.__depth != 1:
            raise InvalidContainerAccessException('DictDB depth mismatch')
        self._db.delete(get_encoded_key(key))

    def __iter__(self):
        raise InvalidContainerAccessException("Iteration not supported in DictDB")


class ArrayDB(object):
    """
    Utility classes wrapping the state DB.
    ArrayDB supports length and iterator, maintains order.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """
    __SIZE = 'size'
    __SIZE_BYTE_KEY = get_encoded_key(__SIZE)

    def __init__(self, var_key: K, db: 'IconScoreDatabase', value_type: type) -> None:
        prefix: bytes = ContainerUtil.create_db_prefix(type(self), var_key)
        self._db = db.get_sub_db(prefix)
        self.__value_type = value_type
        self.__size = self.__get_size_from_db()

    def put(self, value: V) -> None:
        """
        Puts the value at the end of array

        :param value: value to add
        """
        size: int = self.__size
        self.__put(size, value)
        self.__set_size(size + 1)

    def pop(self) -> Optional[V]:
        """
        Gets and removes last added value

        :return: last added value
        """
        size: int = self.__size
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
        return self[index]

    def __get_size_from_db(self) -> int:
        return ContainerUtil.decode_object(self._db.get(self.__SIZE_BYTE_KEY), int)

    def __set_size(self, size: int) -> None:
        self.__size = size
        byte_value = ContainerUtil.encode_value(size)
        self._db.put(self.__SIZE_BYTE_KEY, byte_value)

    def __put(self, index: int, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(get_encoded_key(index), byte_value)

    def __iter__(self):
        return self._get_generator(self._db, self.__size, self.__value_type)

    def __len__(self):
        return self.__size

    def __setitem__(self, index: int, value: V) -> None:
        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        size: int = self.__size

        # Negative index means that you count from the right instead of the left.
        if index < 0:
            index += size

        if 0 <= index < size:
            self.__put(index, value)
        else:
            raise InvalidParamsException('ArrayDB out of index')

    def __getitem__(self, index: int) -> V:
        return self._get(self._db, self.__size, index, self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False

    @classmethod
    def _get(cls, db: Union['IconScoreDatabase', 'IconScoreSubDatabase'], size: int, index: int, value_type: type) -> V:
        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        # Negative index means that you count from the right instead of the left.
        if index < 0:
            index += size

        if 0 <= index < size:
            key: bytes = get_encoded_key(index)
            return ContainerUtil.decode_object(db.get(key), value_type)

        raise InvalidParamsException('ArrayDB out of index')

    @classmethod
    def _get_generator(cls, db: Union['IconScoreDatabase', 'IconScoreSubDatabase'], size: int, value_type: type):
        for index in range(size):
            yield cls._get(db, size, index, value_type)


class VarDB(object):
    """
    Utility classes wrapping the state DB.
    VarDB can be used to store simple key-value state.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """

    def __init__(self, var_key: K, db: 'IconScoreDatabase', value_type: type) -> None:
        # Use var_key as a db prefix in the case of VarDB
        self._db = db.get_sub_db(VAR_DB_ID)
        self.__var_byte_key = get_encoded_key(var_key)
        self.__value_type = value_type

    def set(self, value: V) -> None:
        """
        Sets the value

        :param value: a value to be set
        """
        byte_value = ContainerUtil.encode_value(value)
        self._db.put(self.__var_byte_key, byte_value)

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        return ContainerUtil.decode_object(self._db.get(self.__var_byte_key), self.__value_type)

    def remove(self) -> None:
        """
        Deletes the value
        """
        self._db.delete(self.__var_byte_key)


def get_default_value(value_type: type) -> Any:
    if value_type == int:
        return 0
    elif value_type == str:
        return ""
    elif value_type == bool:
        return False
    return None
