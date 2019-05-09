# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING

from .candidate import Candidate
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..base.address import Address
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


class CandidateStorage(object):

    def __init__(self, db: 'ContextDatabase'):
        """Constructor

        :param db: (Database) state db wrapper
        """
        self._db: 'ContextDatabase' = db

    def close(self):
        """Close the embedded database.
        """
        if self._db:
            self._db = None

    def is_candidate(self,
                     context: 'IconScoreContext',
                     address: 'Address') -> bool:

        key: bytes = Candidate.make_key(address)
        return self._db.get(context, key) is not None

    def get_candidate(self,
                      context: 'IconScoreContext',
                      address: 'Address') -> 'Candidate':

        key: bytes = Candidate.make_key(address)
        value: bytes = self._db.get(context, key)
        if value is None:
            raise InvalidParamsException("get_candidate: value is None")
        candidate: 'Candidate' = Candidate.from_bytes(value, address)
        return candidate

    def put_candidate(self,
                      context: 'IconScoreContext',
                      prep_candidate: 'Candidate'):

        key: bytes = Candidate.make_key(prep_candidate.address)
        value: bytes = prep_candidate.to_bytes()
        self._db.put(context, key, value)

    def delete_candidate(self,
                         context: 'IconScoreContext',
                         address: 'Address'):

        key: bytes = Candidate.make_key(address)
        self._db.delete(context, key)

    def get_prep_candidates(self) -> iter:
        return self._db.key_value_db.get_sub_db(Candidate.prefix).iterator()
