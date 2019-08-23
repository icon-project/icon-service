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

from iconservice.database.db import ExternalDatabase
from tests.mock_db import MockPlyvelDB


class MockIissDataBase(ExternalDatabase):
    def __init__(self, db) -> None:
        super().__init__(db)

    @staticmethod
    def from_path(path: str,
                  create_if_missing: bool = True) -> 'MockIissDataBase':
        """
        :param path: db path
        :param create_if_missing:
        :return: KeyValueDatabase instance
        """
        db = MockPlyvelDB(MockPlyvelDB.make_db())
        return MockIissDataBase(db)

    def get_sub_db(self, prefix: bytes) -> 'MockIissDataBase':
        """Return a new prefixed database.

        :param prefix: (bytes): prefix to use
        """
        return MockIissDataBase(self._db.prefixed_db(prefix))
