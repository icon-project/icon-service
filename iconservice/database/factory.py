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


import os

from .db import ContextDatabase
from ..base.address import Address


class DatabaseFactory(object):
    """Create db accessor to manipulate a state db.
    """

    def __init__(self, state_db_root_path: str):
        """Constructor
        """
        self.__state_db_root_path = state_db_root_path

    def create_by_address(self, address: Address) -> ContextDatabase:
        """Create a state db with the given address.

        :param address:
        :return: plyvel db object
        """
        name = address.body.hex()
        path = os.path.join(self.__state_db_root_path, name)

        return ContextDatabase.from_address_and_path(address, path)

    def create_by_name(self, name: str) -> ContextDatabase:
        """Create a state db with the given address.

        :param address:
        :return: plyvel db object
        """
        path = os.path.join(self.__state_db_root_path, name)

        return ContextDatabase.from_address_and_path(address=None, path=path)

    def is_exist(self, address: Address) -> bool:
        """ Check DB exist

        :param address:
        :return:
        """

        name = address.body.hex()
        path = os.path.join(self.__state_db_root_path, name)
        var = os.path.isdir(path)
        return var
