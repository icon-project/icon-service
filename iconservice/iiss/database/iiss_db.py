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

from typing import TYPE_CHECKING

import plyvel

from ...database.db import KeyValueDatabase

if TYPE_CHECKING:
    from ...database.db import KeyValueDatabase


# todo: actually there is no diff with KeyValueDatabase, so consider just using KeyValueDatabase
# todo: could be removed
class IissDatabase(KeyValueDatabase):
    def __init__(self, db: plyvel.DB) -> None:
        super().__init__(db)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'IissDatabase':
        """
        :param path: db path
        :param create_if_missing:
        :return: KeyValueDatabase instance
        """
        db = plyvel.DB(path, create_if_missing=create_if_missing)
        return IissDatabase(db)

    def get_sub_db(self, prefix: bytes) -> 'IissDatabase':
        """Return a new prefixed database.

        :param prefix: (bytes): prefix to use
        """
        return IissDatabase(self._db.prefixed_db(prefix))

    # todo: consider more good method name
    def reset_db(self, path, create_if_missing: bool = True):
        self.close()
        self._db: plyvel.DB = plyvel.DB(path, create_if_missing=create_if_missing)
