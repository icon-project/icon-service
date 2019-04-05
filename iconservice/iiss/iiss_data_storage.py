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
from typing import TYPE_CHECKING, Any

from .database.iiss_db import IissDatabase


class IissDataStorage(object):
    _CURRENT_IISS_DB_NAME = "current"
    _PREVIOUS_IISS_DB_NAME = "previous"

    def __init__(self) -> None:
        """Constructor
        """
        self._db = None

    def open(self, path) -> None:
        db_path = os.path.join(path, self._CURRENT_IISS_DB_NAME)
        self._db = IissDatabase.from_path(db_path, create_if_missing=True)

    def close(self) -> None:
        """Close the embedded database.
        """
        if self._db:
            self._db = None

    def put(self, batch: dict, iiss_data: Any) -> None:
        pass

    def commit(self, batch: dict) -> None:
        pass
