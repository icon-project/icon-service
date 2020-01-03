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

from abc import ABC

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


class EngineBase(ABC):
    def __init__(self):
        pass

    def open(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def rollback(self, context: 'IconScoreContext', block_height: int, block_hash: bytes):
        pass


class StorageBase(ABC):

    def __init__(self, db: 'ContextDatabase'):
        """Constructor

        :param db: (Database) state db wrapper
        """
        self._db = db

    def open(self, *args, **kwargs):
        pass

    def close(self, context: 'IconScoreContext'):
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None

    def rollback(self, context: 'IconScoreContext', block_height: int, block_hash: bytes):
        pass
