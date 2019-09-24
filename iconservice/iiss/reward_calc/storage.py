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
from typing import TYPE_CHECKING, Optional, Tuple

from iconcommons import Logger

from ...iconscore.icon_score_context import IconScoreContext
from ...iiss.reward_calc.data_creator import DataCreator
from ..reward_calc.msg_data import TxData, Header
from ...base.exception import DatabaseException
from ...database.db import KeyValueDatabase
from ...icon_constant import DATA_BYTE_ORDER, REV_IISS, RC_DATA_VERSION_TABLE, RC_DB_VERSION_0, IISS_LOG_TAG
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..reward_calc.msg_data import Data


def get_rc_version(revision: int) -> int:
    if revision < REV_IISS:
        return RC_DB_VERSION_0

    version: Optional[int] = RC_DATA_VERSION_TABLE.get(revision)
    if version is None:
        return get_rc_version(revision - 1)
    return version


class Storage(object):
    """Manages RC DB which Reward Calculator will use to calculate a reward for each address

    """

    _CURRENT_IISS_DB_NAME = "current_db"
    _IISS_RC_DB_NAME_PREFIX = "iiss_rc_db_"

    _KEY_FOR_GETTING_LAST_TRANSACTION_INDEX = b'last_transaction_index'
    _KEY_FOR_CALC_RESPONSE_FROM_RC = b'calc_response_from_rc'
    _KEY_FOR_VERSION_AND_REVISION = b'version_and_revision'

    def __init__(self):
        self._path: str = ""
        self._db: Optional['KeyValueDatabase'] = None
        # 'None' if open() is not called else 'int'
        self._db_iiss_tx_index: Optional[int] = None

    def open(self, context: IconScoreContext, path: str):
        revision: int = context.revision

        if not os.path.exists(path):
            raise DatabaseException(f"Invalid IISS DB path: {path}")
        self._path = path

        current_db_path = os.path.join(path, self._CURRENT_IISS_DB_NAME)
        self._db = KeyValueDatabase.from_path(current_db_path, create_if_missing=True)
        self._db_iiss_tx_index = self._load_last_transaction_index()
        self._supplement_db(context, revision)

    def _supplement_db(self, context: 'IconScoreContext', revision: int):
        # Method that supplement db which is made by previous icon service version
        rc_version, _ = self.get_version_and_revision()
        if revision >= REV_IISS:
            if rc_version == -1:
                self.put_version_and_revision(revision)

            # on first change point.
            # we have to put init Header for RC
            if self._db.get(Header.PREFIX) is None:
                rc_version, rc_revision = self.get_version_and_revision()
                end_block_height: int = context.storage.iiss.get_end_block_height_of_calc(context)
                calc_period: int = context.storage.iiss.get_calc_period(context)
                prev_end_calc_block_height: int = end_block_height - calc_period

                # if this point is new calc start point ...
                # we have to set block height in header data.
                if prev_end_calc_block_height == context.block.height:
                    end_block_height: int = context.block.height
                header: 'Header' = DataCreator.create_header(rc_version, end_block_height, rc_revision)
                self.put_data_directly(header)

                Logger.debug(tag=IISS_LOG_TAG, msg=f"No header data. Put Header to db on open: {str(header)}")

    def put_data_directly(self, iiss_data: 'Data'):
        temp_rc_batch: list = []
        self.put(temp_rc_batch, iiss_data)
        self.commit(temp_rc_batch)

    def close(self):
        """Close the embedded database.
        """
        if self._db:
            self._db.close()
            self._db = None

    def put_calc_response_from_rc(self, iscore: int, block_height: int):
        version = 0
        response_from_rc: bytes = MsgPackForDB.dumps([version, iscore, block_height])
        self._db.put(self._KEY_FOR_CALC_RESPONSE_FROM_RC, response_from_rc)

    def get_calc_response_from_rc(self) -> Tuple[int, int]:
        response_from_rc: Optional[bytes] = self._db.get(self._KEY_FOR_CALC_RESPONSE_FROM_RC)
        if response_from_rc is None:
            return -1, -1
        response_from_rc: list = MsgPackForDB.loads(response_from_rc)
        version = response_from_rc[0]
        iscore = response_from_rc[1]
        block_height = response_from_rc[2]

        return iscore, block_height

    @staticmethod
    def put(batch: list, iiss_data: 'Data'):
        Logger.debug(tag=IISS_LOG_TAG, msg=f"put data: {str(iiss_data)}")
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
        rc_block_batch.clear()

    # todo: naming
    def put_version_and_revision(self, revision: int):
        version: int = get_rc_version(revision)
        version_and_revision: bytes = MsgPackForDB.dumps([version, revision])
        self._db.put(self._KEY_FOR_VERSION_AND_REVISION, version_and_revision)

    def get_version_and_revision(self) -> Tuple[int, int]:
        version_and_revision: Optional[bytes] = self._db.get(self._KEY_FOR_VERSION_AND_REVISION)
        version: int = -1
        revision: int = -1
        if version_and_revision is None:
            return version, revision
        else:
            version_and_revision: list = MsgPackForDB.loads(version_and_revision)
        version: int = version_and_revision[0]
        revision: int = version_and_revision[1]
        return version, revision

    def _load_last_transaction_index(self) -> int:
        encoded_last_index: Optional[bytes] = self._db.get(self._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX)
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

        if os.path.exists(current_db_path):
            os.rename(current_db_path, iiss_rc_db_path)
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

        self._db = KeyValueDatabase.from_path(current_db_path)
        self._db_iiss_tx_index = -1

        return iiss_rc_db_path
