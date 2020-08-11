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

from .container_db.score_db import ScoreDatabase, ScoreSubDatabase
from .container_db.utils import Utils
from .context.context import ContextContainer
from ..base.exception import InvalidContainerAccessException, InvalidParamsException
from ..database.db import IconScoreDatabase, IconScoreSubDatabase
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
    pass


def make_constructor_key_elements(
        keys: List[K],
        container_id: bytes,
) -> List['KeyElement']:
    return _make_encoded_key_elements_in_container_db(
        keys=keys,
        container_id=container_id,
        state=KeyElementState.IS_CONTAINER | KeyElementState.IS_CONSTRUCTOR
    )


def make_key_elements(
        keys: List[K],
        container_id: bytes,
) -> List['KeyElement']:
    return _make_encoded_key_elements_in_container_db(
        keys=keys,
        container_id=container_id,
        state=KeyElementState.IS_CONTAINER
    )


def _make_encoded_key_elements_in_container_db(
        keys: List[K],
        container_id: bytes,
        state: 'KeyElementState'
) -> List['KeyElement']:
    tmp_keys: List[bytes] = []
    for key in keys:
        tmp_keys.append(Utils.encode_key(key))
    return [KeyElement(
        keys=tmp_keys,
        container_id=container_id,
        state=state
    )]


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
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase'],
            value_type: type,
            depth: int = 1,
    ):
        self.__value_type: type = value_type
        self.__depth: int = depth

        self._db: 'IconScoreSubDatabase' = self._get_init_db(
            db=db,
            key=key
        )

    def remove(self, key: K):
        self._remove(key)

    def _remove(self, key: K):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        keys: List['KeyElement'] = make_key_elements(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        self._db.delete(keys=keys)

    def __setitem__(self, key: K, value: V):
        if not self._is_leaf:
            raise InvalidContainerAccessException('DictDB depth is not leaf')

        keys: List['KeyElement'] = make_key_elements(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = Utils.encode_value(value)
        self._db.put(keys=keys, value=value)

    def __getitem__(self, key: K) -> Any:
        if not self._is_leaf:
            return DictDB(
                key=key,
                db=self._db,
                value_type=self.__value_type,
                depth=self.__depth - 1
            )

        keys: List['KeyElement'] = make_key_elements(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = self._db.get(keys=keys)
        return Utils.decode_object(value, self.__value_type)

    def __delitem__(self, key: K):
        self._remove(key)

    def __contains__(self, key: K) -> bool:
        keys: List['KeyElement'] = make_key_elements(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        value: bytes = self._db.get(keys=keys)
        return value is not None

    def __iter__(self):
        raise InvalidContainerAccessException("Iteration not supported in DictDB")

    @property
    def _is_leaf(self) -> bool:
        return self.__depth == 1

    @classmethod
    def _get_init_db(
            cls,
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase'],
            key: K) -> 'IconScoreSubDatabase':

        keys: List['KeyElement'] = make_constructor_key_elements(
            keys=[key],
            container_id=DICT_DB_ID,
        )
        if isinstance(db, IconScoreSubDatabase):
            init_db: 'IconScoreSubDatabase' = db.get_sub_db(keys=keys)
        else:
            init_db: 'IconScoreSubDatabase' = db._db.get_sub_db(keys=keys)
        if not isinstance(init_db, IconScoreSubDatabase):
            raise InvalidParamsException(f"Invalid IconScoreDatabase type: {type(db)}")
        return init_db


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
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase'],
            value_type: type,
            depth: int = 1
    ):
        self.__value_type = value_type
        self.__depth = depth

        self._db: 'IconScoreSubDatabase' = self._get_init_db(
            db=db,
            key=key
        )
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
                db=self._db,
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

        keys: List['KeyElement'] = make_key_elements(
            keys=[index],
            container_id=ARRAY_DB_ID,
        )
        self._db.delete(keys=keys)
        self.__set_size(index)
        return last_val

    def __get_size_from_db(self) -> int:
        keys: List['KeyElement'] = self._get_size_key()
        value: bytes = self._db.get(keys=keys)
        return Utils.decode_object(value, int)

    def __set_size(self, size: int):
        self.__legacy_size: int = size
        keys: List['KeyElement'] = self._get_size_key()
        value: bytes = Utils.encode_value(size)
        self._db.put(keys=keys, value=value)

    def __put(self, index: int, value: V):
        keys: List['KeyElement'] = make_key_elements(
            keys=[index],
            container_id=ARRAY_DB_ID,
        )
        value = Utils.encode_value(value)
        self._db.put(keys=keys, value=value)

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
                db=self._db,
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
            db: 'IconScoreSubDatabase',
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
            keys: List['KeyElement'] = make_key_elements(
                keys=[index],
                container_id=ARRAY_DB_ID,
            )
            value: bytes = db.get(keys=keys)
            return Utils.decode_object(value, value_type)
        raise InvalidParamsException('ArrayDB out of index')

    @classmethod
    def _get_generator(
            cls,
            db: 'IconScoreSubDatabase',
            size: int,
            value_type: type
    ):
        for index in range(size):
            yield cls._get(db, size, index, value_type)

    @classmethod
    def _get_size_key(cls) -> List['KeyElement']:
        return make_key_elements(
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

    @classmethod
    def _get_init_db(
            cls,
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase'],
            key: K) -> 'IconScoreSubDatabase':
        keys: List['KeyElement'] = make_constructor_key_elements(
            keys=[key],
            container_id=ARRAY_DB_ID,
        )
        if isinstance(db, IconScoreSubDatabase):
            init_db: 'IconScoreSubDatabase' = db.get_sub_db(keys=keys)
        else:
            init_db: 'IconScoreSubDatabase' = db._db.get_sub_db(keys=keys)
        if not isinstance(init_db, IconScoreSubDatabase):
            raise InvalidParamsException(f"Invalid IconScoreDatabase type: {type(db)}")
        return init_db


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
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase'],
            value_type: type
    ):
        # Use var_key as a db prefix in the case of VarDB

        self.__key = var_key
        self.__value_type = value_type

        self._db: 'IconScoreDatabase' = self._get_init_db(db)

    def set(self, value: V):
        """
        Sets the value

        :param value: a value to be set
        """
        keys: List['KeyElement'] = self._get_keys()
        value: bytes = Utils.encode_value(value=value)
        self._db.put(
            keys=keys,
            value=value,
        )

    def get(self) -> Optional[V]:
        """
        Gets the value

        :return: value of the var db
        """
        keys: List['KeyElement'] = self._get_keys()
        value: bytes = self._db.get(
            keys=keys,
        )

        return Utils.decode_object(value, self.__value_type)

    def remove(self):
        """
        Deletes the value
        """
        keys: List['KeyElement'] = self._get_keys()
        self._db.delete(
            keys=keys,
        )

    def _get_keys(self) -> List['KeyElement']:
        return make_constructor_key_elements(
            keys=[self.__key],
            container_id=VAR_DB_ID,
        )

    @classmethod
    def _get_init_db(
            cls,
            db: Union['ScoreDatabase', 'ScoreSubDatabase', 'IconScoreSubDatabase']
    ) -> 'IconScoreDatabase':

        if isinstance(db, IconScoreSubDatabase):
            init_db: 'IconScoreSubDatabase' = db
        else:
            init_db: 'IconScoreDatabase' = db._db

        if not isinstance(init_db, (IconScoreDatabase, IconScoreSubDatabase)):
            raise InvalidParamsException(f"Invalid IconScoreDatabase type: {type(db)}")
        return init_db
