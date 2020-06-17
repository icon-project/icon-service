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
from typing import TYPE_CHECKING, Optional, Tuple, Iterable, Union

import plyvel

from iconcommons.logger import Logger
from .batch import TransactionBatchValue
from .score_db.utils import DICT_DB_ID, RLPPrefix, make_rlp_prefix_list
from ..base.exception import DatabaseException, InvalidParamsException, AccessDeniedException
from ..icon_constant import ICON_DB_LOG_TAG, IconScoreContextType, Revision
from ..iconscore.context.context import ContextGetter

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


def _is_db_writable_on_context(context: 'IconScoreContext'):
    """Check if db is writable on a given context

    :param context:
    :return:
    """
    if context is None:
        return True
    else:
        return not context.readonly


class KeyValueDatabase(object):
    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'KeyValueDatabase':
        """

        :param path: db path
        :param create_if_missing:
        :return: KeyValueDatabase instance
        """
        db = plyvel.DB(path, create_if_missing=create_if_missing)
        return KeyValueDatabase(db)

    def __init__(self, db: plyvel.DB) -> None:
        """Constructor

        :param db: plyvel db instance
        """
        self._db = db

    def get(self, key: bytes) -> bytes:
        """Get the value for the specified key.

        :param key: (bytes): key to retrieve
        :return: value for the specified key, or None if not found
        """
        return self._db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """Set a value for the specified key.

        :param key: (bytes): key to set
        :param value: (bytes): data to be stored
        """
        self._db.put(key, value)

    def delete(self, key: bytes) -> None:
        """Delete the key/value pair for the specified key.

        :param key: key to delete
        """
        self._db.delete(key)

    def close(self) -> None:
        """Close the database.
        """
        if self._db:
            self._db.close()
            self._db = None

    def get_sub_db(self, prefix: bytes) -> 'KeyValueDatabase':
        """Return a new prefixed database.

        :param prefix: (bytes): prefix to use
        """
        return KeyValueDatabase(self._db.prefixed_db(prefix))

    def iterator(self) -> iter:
        return self._db.iterator()

    def write_batch(self, it: Iterable[Tuple[bytes, Optional[bytes]]]) -> int:
        """Write a batch to the database for the specified states dict.

        :param it: iterable which return tuple(key, value)
            key: bytes
            value: optional bytes
        :return: the number of key-value pairs written
        """
        size = 0

        if it is None:
            return size

        with self._db.write_batch() as wb:
            for key, value in it:
                if value:
                    wb.put(key, value)
                else:
                    wb.delete(key)

                size += 1

        return size


class DatabaseObserver(object):
    """ An abstract class of database observer.
    """

    def __init__(self,
                 get_func: callable, put_func: callable, delete_func: callable):
        self.__get_func = get_func
        self.__put_func = put_func
        self.__delete_func = delete_func

    def on_get(self, context: 'IconScoreContext', key: bytes, value: bytes):
        """
        Invoked when `get` is called in `ContextDatabase`

        :param context: SCORE context
        :param key: key
        :param value: value
        """
        if not self.__get_func:
            Logger.warning('__get_func is None', ICON_DB_LOG_TAG)
        self.__get_func(context, key, value)

    def on_put(self,
               context: 'IconScoreContext',
               key: bytes,
               old_value: bytes,
               new_value: bytes):
        """Invoked when `put` is called in `ContextDatabase`.

        :param context: SCORE context
        :param key: key
        :param old_value: old value
        :param new_value: new value
        """
        if not self.__put_func:
            Logger.warning('__put_func is None', ICON_DB_LOG_TAG)
        self.__put_func(context, key, old_value, new_value)

    def on_delete(self,
                  context: 'IconScoreContext',
                  key: bytes,
                  old_value: bytes):
        """Invoked when `delete` is called in `ContextDatabase`.


        :param context: SCORE context
        :param key: key
        :param old_value:
        """
        if not self.__delete_func:
            Logger.warning('__delete_func is None', ICON_DB_LOG_TAG)
        self.__delete_func(context, key, old_value)


class ContextDatabase(object):
    """Database for an IconScore only used in the inside of iconservice.

    IconScore cannot access this database directly.
    Cache + LevelDB
    """

    def __init__(self, db: 'KeyValueDatabase', is_shared: bool = False) -> None:
        """Constructor

        :param db: KeyValueDatabase instance
        """
        self.key_value_db = db
        # True: this db is shared with all SCOREs
        self._is_shared = is_shared

    def get(self, context: Optional['IconScoreContext'], key: bytes) -> bytes:
        """Returns value indicated by key from batch or StateDB

        :param context:
        :param key:
        :return: value
        """
        context_type = context.type

        if context_type in (IconScoreContextType.DIRECT, IconScoreContextType.QUERY):
            return self.key_value_db.get(key)
        else:
            return self.get_from_batch(context, key)

    def get_from_batch(self,
                       context: 'IconScoreContext',
                       key: bytes) -> bytes:
        """Returns a value for a given key

        Search order
        1. TransactionBatch
        2. Current BlockBatch
        3. Prev BlockBatch
        4. StateDB

        :param context:
        :param key:

        :return: a value for a given key
        """
        # Find the value from tx_batch, block_batch and prev_block_batches with a given key
        for batch in context.get_batches():
            if key in batch:
                return batch[key].value

        # get value from state_db
        return self.key_value_db.get(key)

    @staticmethod
    def _check_tx_batch_value(context: Optional['IconScoreContext'],
                              key: bytes,
                              include_state_root_hash: bool):
        tx_batch_value: 'TransactionBatchValue' = context.tx_batch.get(key)
        if tx_batch_value is None:
            return

        if not isinstance(tx_batch_value, TransactionBatchValue):
            raise DatabaseException(
                f'Only TransactionBatchValue type is allowed on tx_batch: {type(tx_batch_value)}')
        elif tx_batch_value.include_state_root_hash != include_state_root_hash:
            raise DatabaseException('Do not change the include_state_root_hash on the same data')

    def put(self,
            context: Optional['IconScoreContext'],
            key: bytes,
            value: Optional[bytes]) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        :param value:
        """
        self._put(context, key, value, include_state_root_hash=True)

    def _put(self,
             context: Optional['IconScoreContext'],
             key: bytes,
             value: Optional[bytes],
             include_state_root_hash: bool) -> None:
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to write')

        context_type = context.type

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.put(key, value)
        else:
            self._check_tx_batch_value(context, key, include_state_root_hash)
            context.tx_batch[key] = TransactionBatchValue(value, include_state_root_hash)

    def delete(self,
               context: Optional['IconScoreContext'],
               key: bytes):
        """Delete key from db

        :param context:
        :param key: key to delete from db
        """
        self._delete(context, key, include_state_root_hash=True)

    def _delete(self,
                context: Optional['IconScoreContext'],
                key: bytes,
                include_state_root_hash: bool):
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to delete')

        context_type = context.type

        if context_type == IconScoreContextType.DIRECT:
            self.key_value_db.delete(key)
        else:
            self._check_tx_batch_value(context, key, include_state_root_hash)
            context.tx_batch[key] = TransactionBatchValue(None, include_state_root_hash)

    def close(self, context: 'IconScoreContext') -> None:
        """close db

        :param context:
        """
        if not _is_db_writable_on_context(context):
            raise DatabaseException('No permission to close')

        if not self._is_shared:
            return self.key_value_db.close()

    def write_batch(self,
                    context: 'IconScoreContext',
                    it: Iterable[Tuple[bytes, Optional[bytes]]]):

        if not _is_db_writable_on_context(context):
            raise DatabaseException(
                'write_batch is not allowed on readonly context')

        return self.key_value_db.write_batch(it)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'ContextDatabase':
        db = KeyValueDatabase.from_path(path, create_if_missing)
        return ContextDatabase(db)


class MetaContextDatabase(ContextDatabase):
    def put(self,
            context: Optional['IconScoreContext'],
            key: bytes,
            value: Optional[bytes]) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        :param value:
        """
        self._put(context, key, value, include_state_root_hash=False)

    def delete(self,
               context: Optional['IconScoreContext'],
               key: bytes) -> None:
        """Set the value to StateDB or cache it according to context type

        :param context:
        :param key:
        """
        self._delete(context, key, include_state_root_hash=False)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'MetaContextDatabase':
        db = KeyValueDatabase.from_path(path, create_if_missing)
        return MetaContextDatabase(db)


class IconScoreDatabase(ContextGetter):
    """It is used in IconScore

    IconScore can access its states only through IconScoreDatabase
    """

    def __init__(
            self,
            address: 'Address',
            context_db: 'ContextDatabase',
    ):
        self.address: 'Address' = address
        self._context_db = context_db
        self._observer: Optional['DatabaseObserver'] = None

        # for cache
        self._prefix: bytes = self.address.to_bytes()

    @property
    def is_root(self) -> bool:
        """
        To identify score_db and sub_db instead of isinstance method.
        :return:
        """
        return True

    @property
    def _is_v2(self) -> bool:
        """
        To branch logic for migration DB.
        :return:
        """
        return self._revision >= Revision.CONTAINER_DB_RLP.value

    @property
    def _revision(self) -> int:
        """
        During change revision especially Revision.CONTAINER_DB_RLP,
        Must not apply is_v2 logic yet.
        :return:
        """
        if self._context.is_revision_changed(Revision.CONTAINER_DB_RLP.value):
            return self._context.revision - 1
        else:
            return self._context.revision

    def get(self, key: Union[list, bytes], container_id: bytes = DICT_DB_ID) -> Optional[bytes]:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :param container_id: default DICT_DB_ID
        :return: value for the specified key, or None if not found

        ****** WORNING ******
            In v2, the previous value is not actually removed.
        *********************
        """

        input_key: list = self._make_input_key(key, container_id)

        if self._is_v2:
            final_key: bytes = self._make_final_key(input_key)
            value: Optional[bytes] = self._context_db.get(self._context, final_key)
            if value is None:
                legacy_final_key: bytes = self._make_final_key(input_key, is_legacy=True)
                value: Optional[bytes] = self._context_db.get(self._context, legacy_final_key)
        else:
            final_key: bytes = self._make_final_key(input_key, is_legacy=True)
            value: Optional[bytes] = self._context_db.get(self._context, final_key)

        if self._observer:
            observer_key: bytes = self._get_observer_key(key=key, final_key=final_key)
            self._observer.on_get(self._context, observer_key, value)
        return value

    def put(self, key: Union[list, bytes], value: bytes, container_id: bytes = DICT_DB_ID):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        :param container_id: default DICT_DB_ID

        ****** WORNING ******
            In v2, the previous value is not actually removed.
        *********************
        """

        self._validate_ownership()

        input_key: list = self._make_input_key(key, container_id)

        if self._is_v2:
            final_key: bytes = self._make_final_key(input_key)
        else:
            final_key: bytes = self._make_final_key(input_key, is_legacy=True)

        if self._observer:
            if self._is_v2:
                old_value: Optional[bytes] = self._context_db.get(self._context, final_key)
                if old_value is None:
                    legacy_final_key: bytes = self._make_final_key(input_key, is_legacy=True)
                    old_value: Optional[bytes] = self._context_db.get(self._context, legacy_final_key)
            else:
                old_value: Optional[bytes] = self._context_db.get(self._context, final_key)

            observer_key: bytes = self._get_observer_key(key=key, final_key=final_key)
            if value:
                self._observer.on_put(self._context, observer_key, old_value, value)
            elif old_value:
                # If new value is None, then deletes the field
                self._observer.on_delete(self._context, observer_key, old_value)
        self._context_db.put(self._context, final_key, value)

    def delete(self, key: Union[list, bytes], container_id: bytes = DICT_DB_ID):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        :param container_id: default DICT_DB_ID

        ****** WORNING ******
            In v2, the previous value is not actually removed.
        *********************
        """
        self._validate_ownership()

        input_key: list = self._make_input_key(key, container_id)

        if self._is_v2:
            final_key: bytes = self._make_final_key(input_key)
        else:
            final_key: bytes = self._make_final_key(input_key, is_legacy=True)

        if self._observer:
            if self._is_v2:
                old_value: Optional[bytes] = self._context_db.get(self._context, final_key)
                if old_value is None:
                    legacy_final_key: bytes = self._make_final_key(input_key, is_legacy=True)
                    old_value: Optional[bytes] = self._context_db.get(self._context, legacy_final_key)
            else:
                old_value: Optional[bytes] = self._context_db.get(self._context, final_key)

            # If old value is None, won't fire the callback
            if old_value:
                observer_key: bytes = self._get_observer_key(key=key, final_key=final_key)
                self._observer.on_delete(self._context, observer_key, old_value)
        self._context_db.delete(self._context, final_key)

    def get_sub_db(
            self,
            prefix: Union[list, bytes],
            container_id: bytes = DICT_DB_ID
    ) -> 'IconScoreSubDatabase':
        if not prefix:
            raise InvalidParamsException(
                'Invalid params: '
                'prefix is None in IconScoreDatabase.get_sub_db()')

        prefix: list = self._convert_input_prefix_to_list(prefix=prefix, container_id=container_id)
        return IconScoreSubDatabase(
            address=self.address,
            score_db=self,
            prefix=prefix,
            container_id=container_id
        )

    def close(self):
        self._context_db.close(self._context)

    def set_observer(self, observer: 'DatabaseObserver'):
        self._observer = observer

    def _validate_ownership(self):
        """Prevent a SCORE from accessing the database of another SCORE
        """
        if self._context.current_address != self.address:
            raise AccessDeniedException(
                f"Invalid database ownership: "
                f"{self._context.current_address}, "
                f"{self.address}")

    def _get_observer_key(self, key: bytes, final_key: bytes) -> bytes:
        if not self._is_v2:
            return key
        else:
            return final_key

    def _convert_input_prefix_to_list(self, prefix: Union[list, bytes], container_id: bytes) -> list:
        if isinstance(prefix, bytes):
            if self._is_v2:
                return make_rlp_prefix_list(prefix)
            else:
                return [container_id] + make_rlp_prefix_list(prefix)
        else:
            if self._is_v2:
                return prefix
            else:
                return [container_id] + prefix

    def _make_input_key(self, key: Union[list, bytes], container_id: bytes) -> list:
        input_key: list = self.__convert_input_key(key)
        return self.__combine_container_id_to_key(input_key, container_id)

    def _make_final_key(self, input_key: list, is_legacy: bool = False) -> bytes:
        bytes_list: list = self.__convert_bytes_list(input_key, is_legacy=is_legacy)
        separator: bytes = b'|' if is_legacy else b''
        return self.__concat_key(bytes_list, separator)

    def __combine_container_id_to_key(self, key: list, container_id: bytes) -> list:
        if self._is_v2:
            return [container_id] + key
        else:
            return key

    def __concat_key(self, key: list, separator: bytes) -> bytes:
        """All key is hashed and stored
        to StateDB to avoid key conflicts among SCOREs

        :params key: key passed by SCORE
        :return: key bytes
        """
        return separator.join([self._prefix] + key)

    @classmethod
    def __convert_input_key(cls, key: Union[list, bytes]) -> list:
        if isinstance(key, bytes):
            return make_rlp_prefix_list(key)
        else:
            return key

    @classmethod
    def __convert_bytes_list(
            cls,
            keys: list,
            is_legacy: bool = False
    ) -> list:
        new_keys: list = []
        for v in keys:
            if isinstance(v, RLPPrefix):
                if not is_legacy:
                    new_keys.append(bytes(v))
                else:
                    new_keys.append(v.legacy_key)
            elif isinstance(v, bytes):
                new_keys.append(v)
            else:
                raise InvalidParamsException("Unsupported key")
        return new_keys


class IconScoreSubDatabase:

    def __init__(
            self,
            address: 'Address',
            score_db: 'IconScoreDatabase',
            prefix: list,
            container_id: bytes = DICT_DB_ID
    ):
        if prefix is None:
            raise InvalidParamsException("Invalid prefix")

        self.address: 'Address' = address
        self._score_db: 'IconScoreDatabase' = score_db

        self._prefix: list = prefix
        self._container_id: bytes = container_id

    @property
    def is_root(self) -> bool:
        """
        To identify score_db and sub_db instead of isinstance method.
        :return:
        """
        return False

    def get(self, key: Union[list, bytes]) -> Optional[bytes]:
        """
        Gets the value for the specified key

        :param key: key to retrieve
        :return: value for the specified key, or None if not found
        """
        key: list = self._convert_key(key)
        return self._score_db.get(key=key, container_id=self._container_id)

    def put(self, key: Union[list, bytes], value: bytes):
        """
        Sets a value for the specified key.

        :param key: key to set
        :param value: value to set
        """
        key: list = self._convert_key(key)
        self._score_db.put(key=key, value=value, container_id=self._container_id)

    def delete(self, key: Union[list, bytes]):
        """
        Deletes the key/value pair for the specified key.

        :param key: key to delete
        """
        key: list = self._convert_key(key)
        self._score_db.delete(key=key, container_id=self._container_id)

    def get_sub_db(self, prefix: Union[list, bytes]) -> 'IconScoreSubDatabase':
        if not prefix:
            raise InvalidParamsException(
                'Invalid params: '
                'prefix is None in IconScoreDatabase.get_sub_db()'
            )

        prefix: list = self._convert_input_prefix_to_list(prefix=prefix, container_id=self._container_id)
        return IconScoreSubDatabase(
            address=self.address,
            score_db=self._score_db,
            prefix=self._prefix + prefix,
            container_id=self._container_id
        )

    def close(self):
        self._score_db.close()

    def _convert_key(self, key: Union[list, bytes]) -> list:
        if isinstance(key, bytes):
            return self._prefix + make_rlp_prefix_list(key)
        else:
            return self._prefix + key

    def _convert_input_prefix_to_list(self, prefix: Union[list, bytes], container_id: bytes) -> list:
        return self._score_db._convert_input_prefix_to_list(prefix=prefix, container_id=container_id)
