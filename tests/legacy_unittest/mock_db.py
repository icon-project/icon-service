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

from typing import Optional

from iconservice.database.db import KeyValueDatabase


class MockKeyValueDatabase(KeyValueDatabase):
    """Plyvel database wrapper
    """

    @staticmethod
    def create_db() -> "KeyValueDatabase":
        db = MockPlyvelDB(MockPlyvelDB.make_db())
        return KeyValueDatabase(db)


class MockPlyvelDB(object):
    """Plyvel database wrapper
    """

    @staticmethod
    def make_db() -> dict:
        return dict()

    def __init__(self, db: dict) -> None:
        self._db = db

    def get(self, bytes_key: bytes, default=None, *args, **kwargs) -> Optional[bytes]:
        return self._db.get(bytes_key)

    def put(self, bytes_key: bytes, value: bytes, *args, **kwargs) -> None:
        self._db[bytes_key] = value

    def delete(self, bytes_key: bytes, *args, **kwargs) -> None:
        if bytes_key in self._db:
            del self._db[bytes_key]

    def close(self) -> None:
        pass

    def get_sub_db(self, key: bytes):
        return MockPlyvelDB(self.make_db())

    def iterator(self) -> iter:
        return iter(self._db)

    def prefixed_db(self, bytes_prefix) -> "MockPlyvelDB":
        return MockPlyvelDB(MockPlyvelDB.make_db())

    def write_batch(self, *args, **kwargs) -> "MockWriteBatch":
        return MockWriteBatch(self)


class MockWriteBatch(object):
    """ WriteBatch(DB db, bytes prefix, bool transaction, sync) """

    def clear(self):
        """ WriteBatch.clear(self) """
        pass

    def delete(self, bytes_key):
        """ WriteBatch.delete(self, bytes key) """
        self._db.delete(bytes_key)

    def put(self, bytes_key, value):
        """ WriteBatch.put(self, bytes key, value) """
        self._db.put(bytes_key, value)

    def write(self):
        """ WriteBatch.write(self) """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, db):
        self._db = db
