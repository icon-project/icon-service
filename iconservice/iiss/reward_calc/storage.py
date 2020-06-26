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
import shutil
from collections import namedtuple
from typing import TYPE_CHECKING, Optional, Tuple, List, Set

from iconcommons import Logger
from ..reward_calc.msg_data import Header, TxData, PRepsData, TxType, make_block_produce_info_key
from ...base.exception import DatabaseException, InternalServiceErrorException
from ...database.db import KeyValueDatabase
from ...icon_constant import (
    DATA_BYTE_ORDER, Revision, RC_DATA_VERSION_TABLE, RC_DB_VERSION_0,
    IISS_LOG_TAG, ROLLBACK_LOG_TAG
)
from ...iiss.reward_calc.data_creator import DataCreator
from ...utils import bytes_to_hex
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ...base.address import Address
    from ...database.wal import IissWAL
    from ..reward_calc.msg_data import Data, DelegationInfo
    from ...iconscore.icon_score_context import IconScoreContext


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
    STANDBY_IISS_DB_NAME_PREFIX = "standby_rc_db"
    IISS_RC_DB_NAME_PREFIX = "iiss_rc_db"

    KEY_FOR_GETTING_LAST_TRANSACTION_INDEX = b'last_transaction_index'
    KEY_FOR_CALC_RESPONSE_FROM_RC = b'calc_response_from_rc'
    KEY_FOR_VERSION_AND_REVISION = b'version_and_revision'

    def __init__(self):
        self._path: str = ""
        self._db: Optional['KeyValueDatabase'] = None
        # 'None' if open() is not called else 'int'
        self._db_iiss_tx_index: int = -1

    def open(self, context: 'IconScoreContext', path: str):
        revision: int = context.revision

        if not os.path.exists(path):
            raise DatabaseException(f"Invalid IISS DB path: {path}")
        self._path = path

        self._db = self.create_current_db(path)

        self._db_iiss_tx_index = self._load_last_transaction_index()
        Logger.info(tag=IISS_LOG_TAG, msg=f"last_transaction_index on open={self._db_iiss_tx_index}")

        # todo: check side effect of WAL
        self._supplement_db(context, revision)

    def rollback(self, _context: 'IconScoreContext', block_height: int, block_hash: bytes):
        Logger.info(tag=ROLLBACK_LOG_TAG,
                    msg=f"rollback() start: block_height={block_height} block_hash={bytes_to_hex(block_hash)}")

        if self._db is not None:
            raise InternalServiceErrorException("current_db has been opened on rollback")

        if not os.path.exists(self._path):
            raise DatabaseException(f"Invalid IISS DB path: {self._path}")

        self._db = self.create_current_db(self._path)

        self._db_iiss_tx_index = self._load_last_transaction_index()
        Logger.info(tag=IISS_LOG_TAG, msg=f"last_transaction_index on open={self._db_iiss_tx_index}")

        Logger.info(tag=ROLLBACK_LOG_TAG, msg="rollback() end")

    @property
    def key_value_db(self) -> 'KeyValueDatabase':
        return self._db

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
    def get_standby_rc_db_name(cls, block_height: int) -> str:
        return cls._get_db_name(cls.STANDBY_IISS_DB_NAME_PREFIX, block_height)

    @classmethod
    def get_iiss_rc_db_name(cls, block_height: int) -> str:
        return cls._get_db_name(cls.IISS_RC_DB_NAME_PREFIX, block_height)

    @classmethod
    def _get_db_name(cls, prefix: str, block_height: int) -> str:
        return f"{prefix}_{block_height}"

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
            shutil.move(old_db_path, new_db_path)
            Logger.info(tag=IISS_LOG_TAG, msg=f"Rename db: {old_db_path} -> {new_db_path}")
        else:
            raise DatabaseException("Cannot create IISS DB because of invalid path. Check both IISS "
                                    "current DB path and IISS DB path")

    def replace_db(self, block_height: int) -> 'RewardCalcDBInfo':
        """
        1. Rename current_db to standby_db_{block_height}
        2. Create a new current_db for the next calculation period

        :param block_height: End block height of the current calc period
        :return:
        """

        # rename current db -> standby db
        assert block_height > 0

        self._db.close()

        standby_db_path: str = self.rename_current_db_to_standby_db(self._path, block_height)
        self._db = self.create_current_db(self._path)

        return RewardCalcDBInfo(standby_db_path, block_height)

    @classmethod
    def finalize_iiss_db(cls,
                         prev_end_bh: int,
                         current_db: 'KeyValueDatabase',
                         prev_db_path: str):
        """
        Finalize iiss db before sending to reward calculator (i.e. RC). Process is below
            1. Move last Block produce data to previous iiss_db which is to be sent to RC
            2. db compaction

        :param prev_end_bh: end block height of previous term
        :param current_db: newly created db
        :param prev_db_path: iiss_db path which is to be finalized and sent to RC (must has been closed)
        :return:
        """
        bp_key: bytes = make_block_produce_info_key(prev_end_bh)
        prev_db: 'KeyValueDatabase' = KeyValueDatabase.from_path(prev_db_path)
        cls._move_data_from_current_db_to_prev_db(bp_key,
                                                  current_db,
                                                  prev_db)
        prev_db.close()
        cls._process_db_compaction(prev_db_path)

    @classmethod
    def _move_data_from_current_db_to_prev_db(cls,
                                              key: bytes,
                                              current_db: 'KeyValueDatabase',
                                              prev_db: 'KeyValueDatabase'):
        value: Optional[bytes] = current_db.get(key)
        if value is None:
            return

        current_db.delete(key)
        prev_db.put(key, value)

    @classmethod
    def _process_db_compaction(cls, path: str):
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

        Logger.info(tag=IISS_LOG_TAG, msg=f"Create new current_db")
        return KeyValueDatabase.from_path(current_db_path, create_if_missing=True)

    @classmethod
    def rename_current_db_to_standby_db(cls, rc_data_path: str, block_height: int) -> str:
        current_db_path: str = os.path.join(rc_data_path, cls.CURRENT_IISS_DB_NAME)
        standby_db_name: str = cls.get_standby_rc_db_name(block_height)
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

    def get_total_elected_prep_delegated_snapshot(self) -> int:
        """
        total_elected_prep_delegated_snapshot =
            the delegated amount which the elected P-Reps received at the beginning of this term
            - the delegated amount which unregistered P-Reps received in this term

        This function is only intended for state backward compatibility
        and not used any more after revision is set to 7.
        """

        unreg_preps: Set['Address'] = set()
        db = self._db.get_sub_db(TxData.PREFIX)
        for k, v in db.iterator():
            data: 'TxData' = TxData.from_bytes(v)
            if data.type == TxType.PREP_UNREGISTER:
                unreg_preps.add(data.address)

        db = self._db.get_sub_db(PRepsData.PREFIX)
        preps: Optional[List['DelegationInfo']] = None
        for k, v in db.iterator():
            data: 'PRepsData' = PRepsData.from_bytes(k, v)
            preps = data.prep_list
            break

        ret = 0
        if preps:
            for info in preps:
                if info.address not in unreg_preps:
                    ret += info.value

        Logger.info(tag=IISS_LOG_TAG,
                    msg=f"get_total_elected_prep_delegated_snapshot load: {ret}")

        return ret


class IissDBNameRefactor(object):
    """Change iiss_db name: remove revision from iiss_db name

    """
    _DB_NAME_PREFIX = Storage.IISS_RC_DB_NAME_PREFIX

    @classmethod
    def run(cls, rc_data_path: str) -> int:
        ret = 0

        with os.scandir(rc_data_path) as it:
            for entry in it:
                if entry.is_dir() and entry.name.startswith(cls._DB_NAME_PREFIX):
                    new_name: str = cls._get_db_name_without_revision(entry.name)
                    if not new_name:
                        Logger.info(
                            tag=IISS_LOG_TAG,
                            msg=f"Refactoring iiss_db name has been already done: old={entry.name} "
                                f"rc_data_path={rc_data_path}")
                        break

                    cls._change_db_name(rc_data_path, entry.name, new_name)
                    ret += 1

        return ret

    @classmethod
    def _change_db_name(cls, rc_data_path: str, old_name: str, new_name: str):
        if old_name == new_name:
            return

        src_path: str = os.path.join(rc_data_path, old_name)
        dst_path: str = os.path.join(rc_data_path, new_name)

        try:
            shutil.move(src_path, dst_path)
            Logger.info(tag=IISS_LOG_TAG, msg=f"Renaming iiss_db_name succeeded: old={old_name} new={new_name}")
        except BaseException as e:
            Logger.error(tag=IISS_LOG_TAG,
                         msg=f"Failed to rename iiss_db_name: old={old_name} new={new_name} "
                             f"path={rc_data_path} exception={str(e)}")

    @classmethod
    def _get_db_name_without_revision(cls, name: str) -> Optional[str]:
        # items[0]: block_height, items[1]: revision
        items: List[str] = name[len(cls._DB_NAME_PREFIX) + 1:].split("_")
        if len(items) == 1:
            # No need to rename
            return None

        return f"{cls._DB_NAME_PREFIX}_{items[0]}"
