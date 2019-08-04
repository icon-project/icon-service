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

from typing import TYPE_CHECKING, Optional

from ..database.db import ExternalDatabase
from ..icon_constant import IconScoreContextType
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.batch import ExternalBatch


class Storage(object):
    _KEY_LAST_CALC_END_BLOCK = b'last_calc_end_block'
    _KEY_LAST_TERM_END_BLOCK = b'last_term_end_block'

    def __init__(self):
        self._db: Optional['ExternalDatabase'] = None

    def open(self, path: str):
        self._db = ExternalDatabase.from_path(path, create_if_missing=True)

    def close(self):
        """Close the embedded database.
        """
        if self._db:
            self._db.close()
            self._db = None

    def put_last_calc_end_block(self,
                                batch: 'ExternalBatch',
                                last_end_block_height: int):
        version = 0
        value: bytes = MsgPackForDB.dumps([version, last_end_block_height])
        batch[self._KEY_LAST_CALC_END_BLOCK] = value

    def get_last_calc_end_block(self,
                                context: 'IconScoreContext') -> int:
        value: bytes = self._db_get_tmp_data(context, self._KEY_LAST_CALC_END_BLOCK)
        if value is None:
            return -1
        data: list = MsgPackForDB.loads(value)
        version = data[0]

        return data[1]

    def put_last_term_end_block(self,
                                batch: 'ExternalBatch',
                                last_end_block_height: int):
        version = 0
        value: bytes = MsgPackForDB.dumps([version, last_end_block_height])
        batch[self._KEY_LAST_TERM_END_BLOCK] = value

    def get_last_term_end_block(self, context: 'IconScoreContext') -> int:
        value: bytes = self._db_get_tmp_data(context, self._KEY_LAST_TERM_END_BLOCK)
        if value is None:
            return -1
        data: list = MsgPackForDB.loads(value)
        version = data[0]

        return data[1]

    def commit(self, block_batch: 'ExternalBatch'):

        if len(block_batch) == 0:
            return

        self._db.write_batch(block_batch)

    def _db_get_tmp_data(self,
                         context: 'IconScoreContext',
                         key: bytes) -> bytes:

        if context.type in (IconScoreContextType.DIRECT, IconScoreContextType.QUERY):
            return self._db.get(key)
        else:
            return self._get_from_batch(context, key)

    def _get_from_batch(self,
                        context: 'IconScoreContext',
                        key: bytes) -> bytes:

        block_batch = context.meta_block_batch
        tx_batch = context.meta_tx_batch

        # get value from tx_batch
        if key in tx_batch:
            return tx_batch[key]

        # get value from block_batch
        if key in block_batch:
            return block_batch[key]

        # get value from state_db
        return self._db.get(key)
