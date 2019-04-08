# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

import os
from typing import TYPE_CHECKING

from plyvel import destroy_db

from ..icon_constant import DATA_BYTE_ORDER
from .database.iiss_db import IissDatabase
from .iiss_msg_data import IissTxData

if TYPE_CHECKING:
    from .iiss_msg_data import IissData
    from .database.iiss_db import IissDatabase
    from .database.iiss_batch import IissBatch


class IissDataStorage(object):
    _CURRENT_IISS_DB_NAME = "current_db"
    # todo: rename class variable
    _IISS_RC_DB_NAME_WITHOUT_BLOCK_HEIGHT = "iiss_rc_db_"

    def __init__(self) -> None:
        """Constructor

        :param db: (Database) IISS db wrapper
        """
        self._current_db_path: str = ""
        self._iiss_rc_db_path: str = ""
        self._db: 'IissDatabase' = None

    @property
    def db(self) -> 'IissDatabase':
        return self._db

    def open(self, path: str) -> None:
        if not os.path.exists(path):
            # todo: consider which exception should be raised
            raise Exception
        self._current_db_path = os.path.join(path, self._CURRENT_IISS_DB_NAME)
        self._iiss_rc_db_path = os.path.join(path, self._IISS_RC_DB_NAME_WITHOUT_BLOCK_HEIGHT)
        self._db = IissDatabase.from_path(self._current_db_path, create_if_missing=True)

    def close(self) -> None:
        """Close the embedded database.
        """
        if self._db:
            self._db.close()
            self._db = None

    # todo: consider rename 'put' to 'write_to_batch' or 'put_to_batch'
    def put(self, batch: 'IissBatch', iiss_data: 'IissData') -> None:
        # todo: batch data check logic
        if isinstance(iiss_data, IissTxData):
            iiss_data.index = batch.batch_iiss_tx_index
            batch.increase_iiss_tx_index()

        key: bytes = iiss_data.make_key()
        value: bytes = iiss_data.make_value()
        batch[key] = value

    # todo: consider rename 'commit' to 'write_to_db' or 'put_to_db'
    def commit(self, batch: 'IissBatch') -> None:
        # todo: batch data check logic
        self._db.write_batch(batch)

    def load_last_transaction_index(self) -> int:
        # todo: need to refactor
        tx_key_prefix = IissTxData._prefix
        tx_sub_db: 'IissDatabase' = self._db.get_sub_db(tx_key_prefix.encode())
        last_tx_key, _ = next(tx_sub_db.iterator(reverse=True), (None, None))
        # if there is no tx data, return -1 (as iiss engine increase tx index automatically).
        return int.from_bytes(last_tx_key[len(tx_key_prefix):], DATA_BYTE_ORDER) \
            if last_tx_key is not None else -1

    @staticmethod
    def _check_block_height(block_height: int):
        if block_height <= 0:
            raise Exception

    def create_db_for_calc(self, block_height: int) -> str:
        self._check_block_height(block_height)
        # todo: check before creating db
        self._db.close()

        iiss_rc_db_path = self._iiss_rc_db_path + str(block_height)
        if os.path.exists(self._current_db_path) and not os.path.exists(iiss_rc_db_path):
            os.rename(self._current_db_path, iiss_rc_db_path)
        else:
            # todo: consider which exception should be raised
            raise Exception

        self._db.reset_db(self._current_db_path)
        return iiss_rc_db_path

    def remove_db_for_calc(self, block_height: int) -> None:
        self._check_block_height(block_height)
        iiss_rc_db_path = self._iiss_rc_db_path + str(block_height)

        if os.path.exists(iiss_rc_db_path):
            # todo: consider try except about destroy_db method(when try to remove locked db)
            # this method check the process lock
            destroy_db(iiss_rc_db_path)
        else:
            # todo: consider which exception should be raised
            raise Exception
