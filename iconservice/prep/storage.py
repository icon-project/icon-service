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

from typing import TYPE_CHECKING, Optional

from .data.candidate import Candidate
from ..base.ComponentBase import StorageBase
from ..base.exception import InvalidParamsException
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    PREFIX: bytes = b'prep'
    TERMS_KEY: bytes = PREFIX + b'terms'

    def get_candidate(self, context: 'IconScoreContext', address: 'Address') -> 'Candidate':
        key: bytes = Candidate.make_key(address)
        value: bytes = self._db.get(context, key)

        if value is None:
            raise InvalidParamsException(f"P-Rep candidate not found: {str(address)}")

        candidate = Candidate.from_bytes(value)
        assert address == candidate.address

        return candidate

    def put_candidate(self, context: 'IconScoreContext', candidate: 'Candidate'):
        key: bytes = Candidate.make_key(candidate.address)
        value: bytes = candidate.to_bytes()
        self._db.put(context, key, value)

    def delete_candidate(self, context: 'IconScoreContext', address: 'Address'):
        key: bytes = Candidate.make_key(address)
        self._db.delete(context, key)

    def get_candidate_iterator(self) -> iter:
        with self._db.key_value_db.get_sub_db(Candidate.PREFIX).iterator() as it:
            for _, value in it:
                yield Candidate.from_bytes(value)

    def put_terms(self, context: 'IconScoreContext', data: list):
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.TERMS_KEY, value)

    def get_terms(self, context: 'IconScoreContext') -> Optional[list]:
        value: bytes = self._db.get(context, self.TERMS_KEY)
        if value:
            return MsgPackForDB.loads(value)
        return None
