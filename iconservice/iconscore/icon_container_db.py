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


from typing import TypeVar, Optional, Any, Union, TYPE_CHECKING
from collections import Iterator

from iconservice.utils import int_to_bytes

from ..base.address import Address, AddressPrefix
from ..base.exception import ContainerDBException

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase

K = TypeVar('K', int, str, Address, bytes)
V = TypeVar('V', int, str, Address, bytes, bool)


class ContainerUtil(object):

    @staticmethod
    def encode_key(key: K) -> bytes:
        if key is None:
            raise ContainerDBException('key is None')
        prefix = b'|'

        key_bytes = ContainerUtil.__encode_key(key)
        return key_bytes + prefix

    @staticmethod
    def encode_value(value: V) -> bytes:
        return ContainerUtil.__encode_value(value)

    @staticmethod
    def __encode_key(key: K) -> bytes:
        if isinstance(key, int):
            bytes_key = int_to_bytes(key)
        elif isinstance(key, str):
            bytes_key = key.encode('utf-8')
        elif isinstance(key, Address):
            byte_array = bytearray(key.body)
            byte_array.append(key.prefix)
            bytes_key = bytes(byte_array)
        elif isinstance(key, bytes):
            bytes_key = key
        else:
            raise ContainerDBException(f"can't encode key: {key}")
        return bytes_key

    @staticmethod
    def __encode_value(value: V) -> bytes:
        if isinstance(value, int):
            byte_value = int_to_bytes(value)
        elif isinstance(value, str):
            byte_value = value.encode('utf-8')
        elif isinstance(value, Address):
            byte_array = bytearray(value.body)
            byte_array.append(value.prefix)
            byte_value = bytes(byte_array)
        elif isinstance(value, bool):
            byte_value = int_to_bytes(int(value))
        elif isinstance(value, bytes):
            byte_value = value
        else:
            raise ContainerDBException(f"can't encode value: {value}")
        return byte_value

    @staticmethod
    def decode_object(value: bytes, value_type: type) -> Optional[Union[K, V]]:
        if value is None:
            return get_default_value(value_type)

        obj_value = None
        if value_type == int:
            obj_value = int.from_bytes(value, "big", signed=True)
        elif value_type == str:
            obj_value = value.decode()
        elif value_type == Address:
            prefix = AddressPrefix.EOA if value[-1] == 0 else AddressPrefix.CONTRACT
            obj_value = Address(prefix, value[:-1])
        if value_type == bool:
            obj_value = bool(int(int.from_bytes(value, 'big', signed=True)))
        elif value_type == bytes:
            obj_value = value
        return obj_value

    @staticmethod
    def remove_prefix_from_iters(iter_items: iter) -> iter:
        return ((ContainerUtil.__remove_prefix_from_key(key), value) for key, value in iter_items)

    @staticmethod
    def __remove_prefix_from_key(key_from_bytes: bytes) -> bytes:
        return key_from_bytes[:-1]

    @staticmethod
    def put_to_db(db: 'IconScoreDatabase', db_key: str, container: iter) -> None:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        if isinstance(container, dict):
            ContainerUtil.__put_to_db_internal(sub_db, container.items())
        elif isinstance(container, (list, set, tuple)):
            ContainerUtil.__put_to_db_internal(sub_db, enumerate(container))

    @staticmethod
    def get_from_db(db: 'IconScoreDatabase', db_key: str, *args, value_type: type) -> Optional[K]:
        sub_db = db.get_sub_db(ContainerUtil.encode_key(db_key))
        *args, last_arg = args
        for arg in args:
            sub_db = sub_db.get_sub_db(ContainerUtil.encode_key(arg))

        byte_key = sub_db.get(ContainerUtil.encode_key(last_arg))
        if byte_key is None:
            return get_default_value(value_type)
        return ContainerUtil.decode_object(byte_key, value_type)

    @staticmethod
    def __put_to_db_internal(db: 'IconScoreDatabase', iters: iter) -> None:
        for key, value in iters:
            sub_db = db.get_sub_db(ContainerUtil.encode_key(key))
            if isinstance(value, dict):
                ContainerUtil.__put_to_db_internal(sub_db, value.items())
            elif isinstance(value, (list, set, tuple)):
                ContainerUtil.__put_to_db_internal(sub_db, enumerate(value))
            else:
                db_key = ContainerUtil.encode_key(key)
                db_value = ContainerUtil.encode_value(value)
                db.put(db_key, db_value)


class DictDB(object):

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type, depth: int=1) -> None:
        self.__db = db.get_sub_db(ContainerUtil.encode_key(var_key))
        self.__value_type = value_type
        self.__depth = depth

    def remove(self, key: K) -> None:
        self.__remove(key)

    def __setitem__(self, key: K, value: V) -> None:
        if self.__depth != 1:
            raise ContainerDBException(f'DictDB depth mismatch')
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(ContainerUtil.encode_key(key), byte_value)

    def __getitem__(self, key: K) -> Any:
        if self.__depth == 1:
            return ContainerUtil.decode_object(self.__db.get(ContainerUtil.encode_key(key)), self.__value_type)
        else:
            return DictDB(key, self.__db, self.__value_type, self.__depth-1)

    def __delitem__(self, key):
        self.__remove(key)

    def __remove(self, key: K) -> None:
        if self.__depth != 1:
            raise ContainerDBException(f'DictDB depth mismatch')
        self.__db.delete(ContainerUtil.encode_key(key))


class ArrayDB(Iterator):
    __SIZE = 'size'
    __SIZE_BYTE_KEY = ContainerUtil.encode_key(__SIZE)

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        self.__db = db.get_sub_db(ContainerUtil.encode_key(var_key))
        self.__size = self.__get_size()
        self.__index = 0
        self.__value_type = value_type

    def put(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(ContainerUtil.encode_key(self.__size), byte_value)
        self.__size += 1
        self.__set_size()

    def pop(self) -> Optional[V]:
        if self.__size == 0:
            return None

        last_val = self.get(self.__size-1)
        self.__db.delete(ContainerUtil.encode_key(self.__size))
        self.__size -= 1
        self.__set_size()
        return last_val

    def get(self, index: int=0) -> V:
        if index >= self.__size:
            raise ContainerDBException(f'ArrayDB out of range')
        index_byte_key = ContainerUtil.encode_key(index)
        return ContainerUtil.decode_object(self.__db.get(index_byte_key), self.__value_type)

    def __iter__(self):
        self.__index = 0
        return self

    def __next__(self) -> V:
        if self.__index < self.__size:
            index = self.__index
            self.__index += 1
            return self[index]
        else:
            raise StopIteration

    def __len__(self):
        return self.__size

    def __get_size(self) -> int:
        return ContainerUtil.decode_object(self.__db.get(ArrayDB.__SIZE_BYTE_KEY), int)

    def __set_size(self) -> None:
        sub_db = self.__db
        byte_value = ContainerUtil.encode_value(self.__size)
        sub_db.put(ArrayDB.__SIZE_BYTE_KEY, byte_value)

    def __setitem__(self, index: int, value: V) -> None:
        if index >= self.__size:
            raise ContainerDBException(f'ArrayDB out of range')
        sub_db = self.__db
        byte_value = ContainerUtil.encode_value(value)
        sub_db.put(ContainerUtil.encode_key(index), byte_value)

    def __getitem__(self, index: int) -> V:
        if isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                raise ContainerDBException(f'ArrayDB out of range, {index}')
            sub_db = self.__db
            index_byte_key = ContainerUtil.encode_key(index)
            return ContainerUtil.decode_object(sub_db.get(index_byte_key), self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False


# class QueueDB(Iterator):
#     __SIZE = 'size'
#     __START_INDEX = 'start_index'
#     __END_INDEX = 'end_index'
#     __SIZE_BYTE_KEY = ContainerUtil.encode_key(__SIZE)
#     __START_INDEX_BYTE_KEY = ContainerUtil.encode_key(__START_INDEX)
#     __END_INDEX_BYTE_KEY = ContainerUtil.encode_key(__END_INDEX)
#
#     def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
#         self.__db = db.get_sub_db(ContainerUtil.encode_key(var_key))
#         self.__size = self.__get_size()
#
#         self.__start_index = ContainerUtil.decode_object(self.__db.get(QueueDB.__START_INDEX_BYTE_KEY), int)
#         self.__end_index = ContainerUtil.decode_object(self.__db.get(QueueDB.__END_INDEX_BYTE_KEY), int)
#         self.__index = 0
#         self.__value_type = value_type
#
#     def put(self, value: V) -> None:
#         byte_value = ContainerUtil.encode_value(value)
#         self.__db.put(ContainerUtil.encode_key(self.__end_index), byte_value)
#
#         start_index = self.__start_index
#         end_index = self.__end_index + 1
#         size = self.__size + 1
#
#         self.__set_size(size, start_index, end_index)
#
#     def pop(self) -> None:
#         start_index = self.__start_index
#         self.__db.delete(ContainerUtil.encode_key(start_index))
#
#         start_index += 1
#         end_index = self.__end_index
#         size = self.__size - 1
#         self.__set_size(size, start_index, end_index)
#
#     def __get(self, index: int = 0) -> V:
#         if index >= self.__size:
#             raise ContainerDBException(f'QueueDB out of range')
#
#         return ContainerUtil.decode_object(
#             self.__db.get(ContainerUtil.encode_key(index + self.__start_index)), self.__value_type)
#
#     def __iter__(self):
#         self.__index = 0
#         return self
#
#     def __next__(self) -> V:
#         if self.__index < self.__size:
#             index = self.__index
#             self.__index += 1
#             return self.__get(index)
#         else:
#             raise StopIteration
#
#     def __len__(self):
#         return self.__size
#
#     def __get_size(self) -> int:
#         size = 0
#         db_list_size = ContainerUtil.decode_object(self.__db.get(QueueDB.__SIZE_BYTE_KEY), int)
#         if db_list_size:
#             size = db_list_size
#
#         return size
#
#     def __set_size(self, size: int, start_index: int, end_index: int) -> None:
#         sub_db = self.__db
#         if self.__size != size:
#             byte_value = ContainerUtil.encode_value(self.__size)
#             sub_db.put(QueueDB.__SIZE_BYTE_KEY, byte_value)
#         if self.__start_index != start_index:
#             byte_value = ContainerUtil.encode_value(self.__start_index)
#             sub_db.put(QueueDB.__START_INDEX_BYTE_KEY, byte_value)
#         if self.__end_index != end_index:
#             byte_value = ContainerUtil.encode_value(self.__end_index)
#             sub_db.put(QueueDB.__END_INDEX_BYTE_KEY, byte_value)
#
#     def __setitem__(self, index: int, value: V) -> None:
#         if index >= self.__size:
#             raise ContainerDBException(f'QueueDB out of range')
#
#         sub_db = self.__db
#         db_index = index + self.__start_index
#         byte_value = ContainerUtil.encode_value(value)
#         sub_db.put(ContainerUtil.encode_key(db_index), byte_value)
#
#     def __getitem__(self, index: int) -> V:
#         if isinstance(index, int):
#             if index < 0:
#                 index += len(self)
#             if index < 0 or index >= len(self):
#                 raise ContainerDBException(f'QueueDB out of range, {index}')
#
#             sub_db = self.__db
#             db_index = index + self.__start_index
#             return ContainerUtil.decode_object(sub_db.get(ContainerUtil.encode_key(db_index)), self.__value_type)
#
#     def __contains__(self, item: V) -> bool:
#         for e in self:
#             if e == item:
#                 return True
#         return False


class VarDB(object):

    def __init__(self, var_key: str, db: 'IconScoreDatabase', value_type: type) -> None:
        self.__db = db
        self.__var_byte_key = ContainerUtil.encode_key(var_key)
        self.__value_type = value_type

    def set(self, value: V) -> None:
        byte_value = ContainerUtil.encode_value(value)
        self.__db.put(self.__var_byte_key, byte_value)

    def get(self) -> Optional[V]:
        return ContainerUtil.decode_object(self.__db.get(self.__var_byte_key), self.__value_type)

    def remove(self) -> None:
        self.__db.delete(self.__var_byte_key)


def get_default_value(value_type: type) -> Any:
    if value_type == int:
        return 0
    elif value_type == str:
        return ""
    elif value_type == bytes:
        return b''
    return None
