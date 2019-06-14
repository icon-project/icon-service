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
from typing import TYPE_CHECKING, Optional

from iconcommons import Logger

from ..reward_calc.db import Database as RewardCalcDatabase
from ..reward_calc.msg_data import TxData
from ...base.exception import DatabaseException
from ...icon_constant import DATA_BYTE_ORDER

if TYPE_CHECKING:
    from ..reward_calc.msg_data import Data


class Storage(object):
    _CURRENT_IISS_DB_NAME = "current_db"
    _IISS_RC_DB_NAME_PREFIX = "iiss_rc_db_"

    _KEY_FOR_GETTING_LAST_TRANSACTION_INDEX = b'last_transaction_index'

    def __init__(self):
        self._path: str = ""
        self._db: Optional['RewardCalcDatabase'] = None
        # 'None' if open() is not called else 'int'
        self._db_iiss_tx_index: Optional[int] = None

    def open(self, path: str):
        if not os.path.exists(path):
            raise DatabaseException(f"Invalid IISS DB path: {path}")
        self._path = path

        current_db_path = os.path.join(path, self._CURRENT_IISS_DB_NAME)
        self._db = RewardCalcDatabase.from_path(current_db_path, create_if_missing=True)
        self._db_iiss_tx_index = self._load_last_transaction_index()

    def close(self):
        """Close the embedded database.
        """
        if self._db:
            self._db.close()
            self._db = None

    @staticmethod
    def put(batch: list, iiss_data: 'Data'):
        Logger.debug(f"put data: {str(iiss_data)}", "iiss")
        batch.append(iiss_data)

    def commit(self, rc_block_batch: list):
        if len(rc_block_batch) == 0:
            return

        batch_dict = {}
        for iiss_data in rc_block_batch:
            if isinstance(iiss_data, TxData):
                self._db_iiss_tx_index += 1
                key: bytes = iiss_data.make_key(self._db_iiss_tx_index)
            else:
                key: bytes = iiss_data.make_key()
            value: bytes = iiss_data.make_value()
            batch_dict[key] = value

        if self._db_iiss_tx_index >= 0:
            batch_dict[self._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX] = \
                self._db_iiss_tx_index.to_bytes(8, DATA_BYTE_ORDER)

        self._db.write_batch(batch_dict)

    def _load_last_transaction_index(self) -> int:
        encoded_last_index = self._db.get(self._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX)
        if encoded_last_index is None:
            return -1
        else:
            return int.from_bytes(encoded_last_index, DATA_BYTE_ORDER)

    def create_db_for_calc(self, block_height: int) -> str:
        assert block_height > 0

        self._db.close()
        current_db_path = os.path.join(self._path, self._CURRENT_IISS_DB_NAME)
        iiss_rc_db_name = self._IISS_RC_DB_NAME_PREFIX + str(block_height)
        iiss_rc_db_path = os.path.join(self._path, iiss_rc_db_name)

        if os.path.exists(current_db_path) and not os.path.exists(iiss_rc_db_path):
            os.rename(current_db_path, iiss_rc_db_path)
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

        self._db = RewardCalcDatabase.from_path(current_db_path)
        self._db_iiss_tx_index = -1

        return iiss_rc_db_path
