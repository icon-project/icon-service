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
from collections import namedtuple
from typing import TYPE_CHECKING, Optional, Tuple

from iconcommons import Logger
from ..reward_calc.msg_data import Header, TxData
from ...base.exception import DatabaseException
from ...database.db import KeyValueDatabase
from ...icon_constant import (
    DATA_BYTE_ORDER, Revision, RC_DATA_VERSION_TABLE, RC_DB_VERSION_0, IISS_LOG_TAG, WAL_LOG_TAG
)
from ...iconscore.icon_score_context import IconScoreContext
from ...iiss.reward_calc.data_creator import DataCreator
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ...database.wal import IissWAL
    from ..reward_calc.msg_data import Data


RewardCalcDBInfo = namedtuple('RewardCalcDBInfo', ['path', 'block_height'])


def get_rc_version(revision: int) -> int:
    while revision >= Revision.IISS.value:
        version: int = RC_DATA_VERSION_TABLE.get(revision, -1)
        if version > -1:
            return version

        revision -= 1

    return RC_DB_VERSION_0


def get_version_and_revision(db: 'KeyValueDatabase') -> Tuple[int, int]:
    version_and_revision: Optional[bytes] = db.get(Storage.KEY_FOR_VERSION_AND_REVISION)
    if version_and_revision is None:
        return -1, -1

    version, revision = MsgPackForDB.loads(version_and_revision)
    return version, revision


class Storage(object):
    """Manages RC DB which Reward Calculator will use to calculate a reward for each address

    """

    CURRENT_IISS_DB_NAME = "current_db"
    STANDBY_IISS_DB_NAME_PREFIX = "standby_rc_db_"
    IISS_RC_DB_NAME_PREFIX = "iiss_rc_db_"

    KEY_FOR_GETTING_LAST_TRANSACTION_INDEX = b'last_transaction_index'
    KEY_FOR_CALC_RESPONSE_FROM_RC = b'calc_response_from_rc'
    KEY_FOR_VERSION_AND_REVISION = b'version_and_revision'

    def __init__(self):
        self._path: str = ""
        self._db: Optional['KeyValueDatabase'] = None
        # 'None' if open() is not called else 'int'
        self._db_iiss_tx_index: int = -1

    def open(self, context: IconScoreContext, path: str):
        revision: int = context.revision

        if not os.path.exists(path):
            raise DatabaseException(f"Invalid IISS DB path: {path}")
        self._path = path

        self._db = self.create_current_db(path)
        self._db_iiss_tx_index = self._load_last_transaction_index()
        Logger.info(tag=IISS_LOG_TAG, msg=f"last_transaction_index={self._db_iiss_tx_index}")

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

    @classmethod
    def get_standby_rc_db_name(cls, block_height: int, rc_version: int) -> str:
        return f"{cls.STANDBY_IISS_DB_NAME_PREFIX}{block_height}_{rc_version}"

    def put_data_directly(self, iiss_data: 'Data', tx_index: Optional[int] = None):
        if isinstance(iiss_data, TxData):
            key: bytes = iiss_data.make_key(tx_index)
            value: bytes = iiss_data.make_value()
        else:
            key: bytes = iiss_data.make_key()
            value: bytes = iiss_data.make_value()
        self._db.put(key, value)

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

    def get_tx_index(self, start_calc: bool) -> int:
        tx_index: int = -1
        if start_calc:
            return tx_index
        else:
            return self._db_iiss_tx_index

    @staticmethod
    def put(batch: list, iiss_data: 'Data'):
        Logger.debug(tag=IISS_LOG_TAG, msg=f"put data: {str(iiss_data)}")
        batch.append(iiss_data)

    def commit(self, iiss_wal: 'IissWAL'):
        self._db.write_batch(iiss_wal)
        self._db_iiss_tx_index = iiss_wal.final_tx_index
        Logger.info(tag=IISS_LOG_TAG, msg=f"final_tx_index={iiss_wal.final_tx_index}")

    # todo: naming
    def _put_version_and_revision(self, revision: int):
        version: int = get_rc_version(revision)
        version_and_revision: bytes = MsgPackForDB.dumps([version, revision])
        self._db.put(self.KEY_FOR_VERSION_AND_REVISION, version_and_revision)

    def get_version_and_revision(self) -> Tuple[int, int]:
        return get_version_and_revision(self._db)

    def _load_last_transaction_index(self) -> int:
        encoded_last_index: Optional[bytes] = self._db.get(self.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX)
        if encoded_last_index is None:
            return -1
        else:
            return int.from_bytes(encoded_last_index, DATA_BYTE_ORDER)

    @staticmethod
    def _rename_db(old_db_path: str, new_db_path: str):
        if os.path.exists(old_db_path) and not os.path.exists(new_db_path):
            os.rename(old_db_path, new_db_path)
            Logger.info(tag=IISS_LOG_TAG, msg=f"Rename db: {old_db_path} -> {new_db_path}")
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

    def replace_db(self, block_height: int) -> 'RewardCalcDBInfo':
        """
        1. Rename current_db to standby_db_{block_height}_{rc_version}
        2. Create a new current_db for the next calculation period

        :param block_height: End block height of the current calc period
        :return:
        """

        # rename current db -> standby db
        assert block_height > 0

        rc_version, _ = self.get_version_and_revision()
        rc_version: int = max(rc_version, 0)
        self._db.close()
        # Process compaction before send the RC DB to reward calculator
        self.process_db_compaction(os.path.join(self._path, self.CURRENT_IISS_DB_NAME))

        standby_db_path: str = self.rename_current_db_to_standby_db(self._path, block_height, rc_version)
        self._db = self.create_current_db(self._path)

        return RewardCalcDBInfo(standby_db_path, block_height)

    @classmethod
    def process_db_compaction(cls, path: str):
        """
        There is compatibility issue between C++ levelDB and go levelDB.
        To solve it, should make DB being compacted before reading (from RC).
        :param path: DB path to compact
        :return:
        """
        db = KeyValueDatabase.from_path(path)
        db.close()

    @classmethod
    def create_current_db(cls, rc_data_path: str) -> 'KeyValueDatabase':
        current_db_path = os.path.join(rc_data_path, cls.CURRENT_IISS_DB_NAME)
        return KeyValueDatabase.from_path(current_db_path, create_if_missing=True)

    @classmethod
    def rename_current_db_to_standby_db(cls, rc_data_path: str, block_height: int, rc_version: int) -> str:
        current_db_path: str = os.path.join(rc_data_path, cls.CURRENT_IISS_DB_NAME)
        standby_db_name: str = cls.get_standby_rc_db_name(block_height, rc_version)
        standby_db_path: str = os.path.join(rc_data_path, standby_db_name)

        cls._rename_db(current_db_path, standby_db_path)

        return standby_db_path

    @classmethod
    def rename_standby_db_to_iiss_db(cls, standby_db_path: str) -> str:
        # After change the db name, reward calc manage this db (icon service does not have a authority)
        iiss_db_path: str = cls.IISS_RC_DB_NAME_PREFIX.\
            join(standby_db_path.rsplit(cls.STANDBY_IISS_DB_NAME_PREFIX, 1))

        cls._rename_db(standby_db_path, iiss_db_path)

        return iiss_db_path

    @classmethod
    def scan_rc_db(cls, rc_data_path: str) -> Tuple[str, str, str]:
        """Scan directories that are managed by RewardCalcStorage

        :param rc_data_path: the parent directory of rc_dbs
        :return: current_rc_db_exists(bool), standby_rc_db_path, iiss_rc_db_path
        """
        current_rc_db_path: str = ""
        standby_rc_db_path: str = ""
        iiss_rc_db_path: str = ""

        with os.scandir(rc_data_path) as it:
            for entry in it:
                if entry.is_dir():
                    if entry.name == cls.CURRENT_IISS_DB_NAME:
                        current_rc_db_path: str = os.path.join(rc_data_path, cls.CURRENT_IISS_DB_NAME)
                    elif entry.name.startswith(cls.STANDBY_IISS_DB_NAME_PREFIX):
                        standby_rc_db_path: str = os.path.join(rc_data_path, entry.name)
                    elif entry.name.startswith(cls.IISS_RC_DB_NAME_PREFIX):
                        iiss_rc_db_path: str = os.path.join(rc_data_path, entry.name)

        Logger.info(tag=WAL_LOG_TAG,
                    msg=f"current_rc_db={current_rc_db_path}, "
                        f"standby_rc_db={standby_rc_db_path}, "
                        f"iiss_rc_db={iiss_rc_db_path}")

        return current_rc_db_path, standby_rc_db_path, iiss_rc_db_path
