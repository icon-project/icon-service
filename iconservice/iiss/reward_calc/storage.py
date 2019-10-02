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
from typing import TYPE_CHECKING, Optional, Tuple, Iterable

from iconcommons import Logger

from iconservice.database.wal import IissWAL
from iconservice.iiss.engine import RewardCalcDBInfo
from ..reward_calc.msg_data import Header
from ...base.exception import DatabaseException
from ...database.db import KeyValueDatabase
from ...icon_constant import DATA_BYTE_ORDER, Revision, RC_DATA_VERSION_TABLE, RC_DB_VERSION_0, IISS_LOG_TAG
from ...iconscore.icon_score_context import IconScoreContext
from ...iiss.reward_calc.data_creator import DataCreator
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..reward_calc.msg_data import Data


def get_rc_version(revision: int) -> int:
    if revision < Revision.IISS.value:
        return RC_DB_VERSION_0

    version: Optional[int] = RC_DATA_VERSION_TABLE.get(revision)
    if version is None:
        return get_rc_version(revision - 1)
    return version


class Storage(object):
    """Manages RC DB which Reward Calculator will use to calculate a reward for each address

    """

    _CURRENT_IISS_DB_NAME = "current_rc_db"
    _STANDBY_IISS_DB_NAME_PREFIX = "standby_rc_db_"
    _IISS_RC_DB_NAME_PREFIX = "iiss_rc_db_"

    KEY_FOR_GETTING_LAST_TRANSACTION_INDEX = b'last_transaction_index'
    KEY_FOR_CALC_RESPONSE_FROM_RC = b'calc_response_from_rc'
    KEY_FOR_VERSION_AND_REVISION = b'version_and_revision'

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
        # todo: check side effect of WAL
        self._supplement_db(context, revision)

    def _supplement_db(self, context: 'IconScoreContext', revision: int):
        # Supplement db which is made by previous icon service version (as there is no version, revision and header)
        if revision < Revision.IISS.value:
            return

        rc_version, _ = self.get_version_and_revision()
        if rc_version == -1:
            self._put_version_and_revision(revision)

        # On the first change point.
        # We have to put Header for RC
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

    def put_calc_response_from_rc(self, iscore: int, block_height: int, state_hash: bytes):
        version = 1
        response_from_rc: bytes = MsgPackForDB.dumps([version, iscore, block_height, state_hash])
        self._db.put(self.KEY_FOR_CALC_RESPONSE_FROM_RC, response_from_rc)

    def get_calc_response_from_rc(self) -> Tuple[int, int, Optional[bytes]]:
        response_from_rc: Optional[bytes] = self._db.get(self.KEY_FOR_CALC_RESPONSE_FROM_RC)
        if response_from_rc is None:
            return -1, -1, None
        response_from_rc: list = MsgPackForDB.loads(response_from_rc)
        version = response_from_rc[0]
        if version == 0:
            iscore = response_from_rc[1]
            block_height = response_from_rc[2]
            state_hash = None
        elif version == 1:
            iscore = response_from_rc[1]
            block_height = response_from_rc[2]
            state_hash = response_from_rc[3]
        else:
            raise DatabaseException(f"get_calc_response_from_rc invalid version: {version}")

        return iscore, block_height, state_hash

    def get_tx_index(self, context: 'IconScoreContext') -> int:
        tx_index: int = -1
        start_calc_block_height: int = context.engine.iiss.get_start_block_of_calc(context)
        if start_calc_block_height == context.block.height:
            return tx_index
        else:
            # todo: check if return db data.
            return self._db_iiss_tx_index

    @staticmethod
    def put(batch: list, iiss_data: 'Data'):
        Logger.debug(tag=IISS_LOG_TAG, msg=f"put data: {str(iiss_data)}")
        batch.append(iiss_data)

    def commit(self, iiss_wal: 'IissWAL'):
        self._db.write_batch(iiss_wal)
        self._db_iiss_tx_index = iiss_wal.final_tx_index

    # todo: naming
    def _put_version_and_revision(self, revision: int):
        version: int = get_rc_version(revision)
        version_and_revision: bytes = MsgPackForDB.dumps([version, revision])
        self._db.put(self.KEY_FOR_VERSION_AND_REVISION, version_and_revision)

    def get_version_and_revision(self) -> Tuple[int, int]:
        version_and_revision: Optional[bytes] = self._db.get(self.KEY_FOR_VERSION_AND_REVISION)
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
        encoded_last_index: Optional[bytes] = self._db.get(self.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX)
        if encoded_last_index is None:
            return -1
        else:
            return int.from_bytes(encoded_last_index, DATA_BYTE_ORDER)

    def create_current_db(self, current_db_path: str):
        self._db = KeyValueDatabase.from_path(current_db_path)
        self._db_iiss_tx_index = -1

    @staticmethod
    def _rename_db(old_db_path: str, new_db_path: str):
        if os.path.exists(old_db_path) and not os.path.exists(new_db_path):
            os.rename(old_db_path, new_db_path)
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

    def replace_db(self, block_height: int) -> 'RewardCalcDBInfo':
        # rename current db -> standby db
        assert block_height > 0
        current_db_path: str = os.path.join(self._path, self._CURRENT_IISS_DB_NAME)
        standby_db_path: str = self._rename_current_db_to_standby_db(current_db_path, block_height)

        self.create_current_db(current_db_path)
        return RewardCalcDBInfo(standby_db_path, block_height)

    def _rename_current_db_to_standby_db(self, current_db_path: str, block_height: int) -> str:
        rc_version, _ = self.get_version_and_revision()
        self._db.close()

        if rc_version < 0:
            rc_version: int = 0
        standby_db_name: str = self._STANDBY_IISS_DB_NAME_PREFIX + str(block_height) + '_' + str(rc_version)
        standby_db_path = os.path.join(self._path, standby_db_name)

        self._rename_db(current_db_path, standby_db_path)

        return standby_db_path

    def rename_standby_db_to_iiss_db(self, standby_db_path: Optional[str] = None) -> str:
        # After change the db name, reward calc menage this db (icon service does not have a authority)
        if standby_db_path is None:
            standby_db_path: str = self._get_standby_db_path()

        iiss_db_path: str = self._IISS_RC_DB_NAME_PREFIX.\
            join(standby_db_path.rsplit(self._STANDBY_IISS_DB_NAME_PREFIX, 1))
        self._rename_db(standby_db_path, iiss_db_path)

        return iiss_db_path

    def _get_standby_db_path(self):
        for db_name in os.listdir(self._path):
            if db_name.startswith(self._STANDBY_IISS_DB_NAME_PREFIX):
                standby_db_path: str = os.path.join(self._path, db_name)
                break
        else:
            raise DatabaseException("Standby database not exists")

        return standby_db_path

    # todo: Will be removed
    def create_db_for_calc(self, block_height: int) -> str:
        assert block_height > 0

        rc_version, _ = self.get_version_and_revision()

        self._db.close()
        current_db_path = os.path.join(self._path, self._CURRENT_IISS_DB_NAME)

        if rc_version < 0:
            rc_version: int = 0
        iiss_rc_db_name = self._IISS_RC_DB_NAME_PREFIX + str(block_height) + '_' + str(rc_version)

        iiss_rc_db_path = os.path.join(self._path, iiss_rc_db_name)

        if os.path.exists(current_db_path) and not os.path.exists(iiss_rc_db_path):
            os.rename(current_db_path, iiss_rc_db_path)
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

        self._db = KeyValueDatabase.from_path(current_db_path)
        self._db_iiss_tx_index = -1

        return iiss_rc_db_path
