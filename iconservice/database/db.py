# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

import plyvel


class PlyvelDatabase(object):
    """Plyvel database wrapper
    """

    def __init__(self, path: str, create_if_missing: bool=True) -> None:
        """Constructor

        :param path: db directory path
        :param create_if_missing: if not exist, create db in path
        """
        self.__db = plyvel.DB(path, create_if_missing=create_if_missing)

    def get(self, key: bytes) -> bytes:
        """Get value from db using key

        :param key: db key
        :return: value indicated by key otherwise None
        """
        return self.__db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """Put value into db using key.

        :param key: (bytes): db key
            value(bytes): db에 저장할 데이터
        """
        self.__db.put(key, value)

    def delete(self, key: bytes) -> None:
        """Delete a row

        :param key: delete the row indicated by key.
        """
        self.__db.delete(key)

    def close(self) -> None:
        """Close db
        """
        if self.__db:
            self.__db.close()
            self.__db = None
