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

from typing import Optional, Any, Union, TYPE_CHECKING

from .container_db.utils import Utils
from ..base.exception import InvalidContainerAccessException, InvalidParamsException
from ..database.score_db.utils import (
    DICT_DB_ID,
    ARRAY_DB_ID,
    RLPPrefix,
    VAR_DB_ID,
    K, V,
    make_rlp_prefix_list
)

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase, IconScoreSubDatabase


def make_encoded_rlp_prefix_list(
        prefix: K,
        legacy_key: bytes = None,
        prefix_container_id: bool = False
) -> list:
    prefix: bytes = Utils.encode_key(prefix)
    return make_rlp_prefix_list(
        prefix=prefix,
        legacy_key=legacy_key,
        prefix_container_id=prefix_container_id
    )


class DictDB:
    """
    Utility classes wrapping the state DB.
    DictDB behaves more like python dict.
    DictDB does not maintain order.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """

    def __init__(
            self,
            key: K,
            db: Union['IconScoreDatabase', 'IconScoreSubDatabase'],
            value_type: type,
            depth: int = 1
    ):
        key: list = make_encoded_rlp_prefix_list(prefix=key, prefix_container_id=True)
        if db.is_root:
            self._db: 'IconScoreSubDatabase' = db.get_sub_db(key, DICT_DB_ID)
        else:
            self._db: 'IconScoreSubDatabase' = db.get_sub_db(key)

        self.__value_type = value_type
        self.__depth = depth

    def remove(self, key: K):
        self._remove(key)

    def _remove(self, key: K):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        key: list = make_encoded_rlp_prefix_list(prefix=key)
        self._db.delete(key)

    def __setitem__(self, key: K, value: V):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        key: list = make_encoded_rlp_prefix_list(prefix=key)
        value: bytes = Utils.encode_value(value)
        self._db.put(key, value)

    def __getitem__(self, key: K) -> Any:
        if not self._is_leaf:
            return DictDB(
                key=key,
                db=self._db,
                value_type=self.__value_type,
                depth=self.__depth - 1
            )

        key: list = make_encoded_rlp_prefix_list(prefix=key)
        value: bytes = self._db.get(key)
        return Utils.decode_object(value, self.__value_type)

    def __delitem__(self, key: K):
        self._remove(key)

    def __contains__(self, key: K) -> bool:
        key: list = make_encoded_rlp_prefix_list(prefix=key)
        value: bytes = self._db.get(key)
        return value is not None

    def __iter__(self):
        raise InvalidContainerAccessException("Iteration not supported in DictDB")

    @property
    def _is_leaf(self) -> bool:
        return self.__depth == 1


class ArrayDB:
    """
    Utility classes wrapping the state DB.
    ArrayDB supports length and iterator, maintains order.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """

    def __init__(
            self,
            key: K,
            db: Union['IconScoreDatabase', 'IconScoreSubDatabase'],
            value_type: type,
            depth: int = 1
    ):
        self.__value_type = value_type
        self.__depth = depth

        key: list = make_encoded_rlp_prefix_list(prefix=key, prefix_container_id=True)
        if db.is_root:
            self._db: 'IconScoreSubDatabase' = db.get_sub_db(key, ARRAY_DB_ID)
        else:
            self._db: 'IconScoreSubDatabase' = db.get_sub_db(key)
        self.__size = self.__get_size_from_db()

    def put(self, value: V):
        """
        Puts the value at the end of array

        :param value: value to add
        """
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        size: int = self.__size
        self.__put(size, value)
        self.__set_size(size + 1)

    def get(self, index: int = 0) -> Any:
        """
        Gets the value at index

        :param index: index
        :return: value at the index
        """

        if not self._is_leaf:
            return ArrayDB(
                key=index,
                db=self._db,
                value_type=self.__value_type,
                depth=self.__depth - 1
            )

        return self._get(self._db, self.__size, index, self.__value_type)

    def pop(self) -> Optional[V]:
        """
        Gets and removes last added value

        :return: last added value
        """
        size: int = self.__size
        if size == 0:
            return None

        index = size - 1
        last_val = self._get(self._db, self.__size, index, self.__value_type)

        key: list = make_encoded_rlp_prefix_list(prefix=index)
        self._db.delete(key)
        self.__set_size(index)
        return last_val

    def __get_size_from_db(self) -> int:
        key: list = self._get_size_key()
        value: bytes = self._db.get(key)
        return Utils.decode_object(value, int)

    def __set_size(self, size: int):
        self.__size: int = size
        key: list = self._get_size_key()
        value: bytes = Utils.encode_value(size)
        self._db.put(key, value)

    def __put(self, index: int, value: V):
        key: list = make_encoded_rlp_prefix_list(index)
        value = Utils.encode_value(value)
        self._db.put(key, value)

    def __iter__(self):
        return self._get_generator(self._db, self.__size, self.__value_type)

    def __len__(self):
        return self.__size

    def __setitem__(self, index: int, value: V):
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

    def __getitem__(self, index: int) -> Any:
        if not self._is_leaf:
            return ArrayDB(
                key=index,
                db=self._db,
                value_type=self.__value_type,
                depth=self.__depth - 1
            )
        return self._get(self._db, self.__size, index, self.__value_type)

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False

    @classmethod
    def _get(
            cls,
            db: Union['IconScoreDatabase', 'IconScoreSubDatabase'],
            size: int,
            index: int,
            value_type: type
    ) -> V:

        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        # Negative index means that you count from the right instead of the left.
        if index < 0:
            index += size

        if 0 <= index < size:
            key: list = make_encoded_rlp_prefix_list(prefix=index)
            value: bytes = db.get(key)
            return Utils.decode_object(value, value_type)
        raise InvalidParamsException('ArrayDB out of index')

    @classmethod
    def _get_generator(
            cls,
            db: Union['IconScoreDatabase', 'IconScoreSubDatabase'],
            size: int,
            value_type: type
    ):
        for index in range(size):
            yield cls._get(db, size, index, value_type)

    @classmethod
    def _get_size_key(cls) -> list:
        return make_encoded_rlp_prefix_list(prefix=b'', legacy_key=b'size')

    @property
    def _is_leaf(self) -> bool:
        return self.__depth == 1


class VarDB:
    """
    Utility classes wrapping the state DB.
    VarDB can be used to store simple key-value state.

    :K: [int, str, Address, bytes]
    :V: [int, str, Address, bytes, bool]
    """

    def __init__(
            self,
            var_key: K,
            db: 'IconScoreDatabase',
            value_type: type
    ):
        # Use var_key as a db prefix in the case of VarDB
        self._db = db
        self.__key = var_key
        self.__value_type = value_type

    def set(self, value: V):
        """
        Sets the value

        :param value: a value to be set
        """
        key: list = self._get_key()
        value: bytes = Utils.encode_value(value)
        self._db.put(
            key=key,
            value=value,
            container_id=VAR_DB_ID
        )

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        key: list = self._get_key()
        value: bytes = self._db.get(
            key=key,
            container_id=VAR_DB_ID
        )
        return Utils.decode_object(value, self.__value_type)

    def remove(self):
        """
        Deletes the value
        """
        key: list = self._get_key()
        self._db.delete(key=key, container_id=VAR_DB_ID)

    def _get_key(self) -> list:
        return make_encoded_rlp_prefix_list(prefix=self.__key, prefix_container_id=True)
