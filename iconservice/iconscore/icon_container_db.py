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

from typing import Optional, Any, Union, TYPE_CHECKING, List

from .container_db.score_db import IconScoreDatabase
from .container_db.utils import Utils
from .context.context import ContextContainer
from ..base.exception import InvalidContainerAccessException, InvalidParamsException
from ..database.score_db.utils import (
    DICT_DB_ID,
    ARRAY_DB_ID,
    VAR_DB_ID,
    K, V,
    KeyElement,
    KeyElementState
)
from ..icon_constant import IconScoreContextType, Revision

if TYPE_CHECKING:
    from ..database.db import ScoreSubDatabase


def make_constructor_key_element(
        keys: List[K],
        container_id: bytes,
) -> 'KeyElement':
    return _make_encoded_key_element_in_container_db(
        keys=keys,
        container_id=container_id,
        state=KeyElementState.IS_CONTAINER | KeyElementState.IS_CONSTRUCTOR
    )


def make_key_element(
        keys: List[K],
        container_id: bytes,
) -> 'KeyElement':
    return _make_encoded_key_element_in_container_db(
        keys=keys,
        container_id=container_id,
        state=KeyElementState.IS_CONTAINER
    )


def _make_encoded_key_element_in_container_db(
        keys: List[K],
        container_id: bytes,
        state: 'KeyElementState'
) -> 'KeyElement':
    return KeyElement(
        keys=[Utils.encode_key(k) for k in keys],
        container_id=container_id,
        state=state
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
            db: 'IconScoreDatabase',
            value_type: type,
            depth: int = 1,
    ):
        self.__value_type: type = value_type
        self.__depth: int = depth

        ke: 'KeyElement' = make_constructor_key_element(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        score_sub_db: 'ScoreSubDatabase' = db._db
        self._db: 'ScoreSubDatabase' = score_sub_db.get_sub_db(key=ke)

    def remove(self, key: K):
        self._remove(key)

    def _remove(self, key: K):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        ke: 'KeyElement' = make_key_element(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        self._db.delete(key=ke)

    def __setitem__(self, key: K, value: V):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        ke: 'KeyElement' = make_key_element(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = Utils.encode_value(value)
        self._db.put(key=ke, value=value)

    def __getitem__(self, key: K) -> Any:
        if not self._is_leaf:
            return DictDB(
                key=key,
                db=IconScoreDatabase(db=self._db, is_container_db=True),
                value_type=self.__value_type,
                depth=self.__depth - 1
            )

        ke: 'KeyElement' = make_key_element(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = self._db.get(key=ke)
        return Utils.decode_object(value, self.__value_type)

    def __delitem__(self, key: K):
        self._remove(key)

    def __contains__(self, key: K) -> bool:
        ke: 'KeyElement' = make_key_element(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = self._db.get(key=ke)
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
            db: 'IconScoreDatabase',
            value_type: type,
            depth: int = 1
    ):
        self.__value_type = value_type
        self.__depth = depth

        ke: 'KeyElement' = make_constructor_key_element(
            keys=[key],
            container_id=ARRAY_DB_ID,
        )

        score_sub_db: 'ScoreSubDatabase' = db._db
        self._db: 'ScoreSubDatabase' = score_sub_db.get_sub_db(key=ke)

        self.__legacy_size: int = self.__get_size_from_db()

    @property
    def _is_leaf(self) -> bool:
        return self.__depth == 1

    def put(self, value: V):
        """
        Puts the value at the end of array

        :param value: value to add
        """
        if not self._is_leaf:
            raise InvalidContainerAccessException('ArrayDB depth is not leaf')

        size: int = self.__get_size()
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
                db=IconScoreDatabase(db=self._db, is_container_db=True),
                value_type=self.__value_type,
                depth=self.__depth - 1
            )

        return self._get(
            db=self._db,
            size=self.__get_size(),
            index=index,
            value_type=self.__value_type
        )

    def pop(self) -> Optional[V]:
        """
        Gets and removes last added value

        :return: last added value
        """
        size: int = self.__get_size()
        if size == 0:
            return None

        index: int = size - 1
        last_val = self._get(
            db=self._db,
            size=self.__get_size(),
            index=index,
            value_type=self.__value_type
        )

        ke: 'KeyElement' = make_key_element(
            keys=[index],
            container_id=ARRAY_DB_ID,
        )
        self._db.delete(key=ke)
        self.__set_size(index)
        return last_val

    def __get_size_from_db(self) -> int:
        ke: 'KeyElement' = self._get_size_key()
        value: bytes = self._db.get(key=ke)
        return Utils.decode_object(value, int)

    def __set_size(self, size: int):
        self.__legacy_size: int = size
        ke: 'KeyElement' = self._get_size_key()
        value: bytes = Utils.encode_value(size)
        self._db.put(key=ke, value=value)

    def __put(self, index: int, value: V):
        ke: 'KeyElement' = make_key_element(
            keys=[index],
            container_id=ARRAY_DB_ID,
        )
        value = Utils.encode_value(value)
        self._db.put(key=ke, value=value)

    def __iter__(self):
        return self._get_generator(
            db=self._db,
            size=self.__get_size(),
            value_type=self.__value_type
        )

    def __len__(self):
        return self.__get_size()

    def __setitem__(self, index: int, value: V):
        if not isinstance(index, int):
            raise InvalidParamsException('Invalid index type: not an integer')

        size: int = self.__get_size()

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
                db=IconScoreDatabase(db=self._db),
                value_type=self.__value_type,
                depth=self.__depth - 1
            )
        return self._get(
            db=self._db,
            size=self.__get_size(),
            index=index,
            value_type=self.__value_type
        )

    def __contains__(self, item: V):
        for e in self:
            if e == item:
                return True
        return False

    @classmethod
    def _get(
            cls,
            db: 'ScoreSubDatabase',
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
            ke: 'KeyElement' = make_key_element(
                keys=[index],
                container_id=ARRAY_DB_ID,
            )
            value: bytes = db.get(key=ke)
            return Utils.decode_object(value, value_type)
        raise InvalidParamsException('ArrayDB out of index')

    @classmethod
    def _get_generator(
            cls,
            db: 'ScoreSubDatabase',
            size: int,
            value_type: type
    ):
        for index in range(size):
            yield cls._get(db, size, index, value_type)

    @classmethod
    def _get_size_key(cls) -> 'KeyElement':
        return make_key_element(
            keys=[b'', b'size'],
            container_id=ARRAY_DB_ID,
        )

    def __get_size(self) -> int:
        if self.__is_defective_revision():
            return self.__legacy_size
        else:
            return self.__get_size_from_db()

    @classmethod
    def __is_defective_revision(cls):
        context = ContextContainer._get_context()
        revision = context.revision
        return context.type == IconScoreContextType.INVOKE and revision < Revision.THREE.value


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
            db: Union['IconScoreDatabase'],
            value_type: type
    ):
        # Use var_key as a db prefix in the case of VarDB

        self.__key = var_key
        self.__value_type = value_type

        score_sub_db: 'ScoreSubDatabase' = db._db
        self._db: 'ScoreSubDatabase' = score_sub_db

    def set(self, value: V):
        """
        Sets the value

        :param value: a value to be set
        """
        ke: 'KeyElement' = self._get_key()
        value: bytes = Utils.encode_value(value=value)
        self._db.put(
            key=ke,
            value=value,
        )

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        ke: 'KeyElement' = self._get_key()
        value: bytes = self._db.get(
            key=ke,
        )

        return Utils.decode_object(value, self.__value_type)

    def remove(self):
        """
        Deletes the value
        """
        ke: 'KeyElement' = self._get_key()
        self._db.delete(
            key=ke,
        )

    def _get_key(self) -> 'KeyElement':
        return make_constructor_key_element(
            keys=[self.__key],
            container_id=VAR_DB_ID,
        )
