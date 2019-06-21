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

from .data.prep import PRep
from ..base.ComponentBase import StorageBase
from ..base.exception import InvalidParamsException
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    PREFIX: bytes = b'prep'
    TERM_KEY: bytes = PREFIX + b'term'

    def get_prep(self, context: 'IconScoreContext', address: 'Address') -> 'PRep':
        key: bytes = PRep.make_key(address)
        value: bytes = self._db.get(context, key)

        if value is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        prep = PRep.from_bytes(value)
        assert address == prep.address

        return prep

    def put_prep(self, context: 'IconScoreContext', prep: 'PRep'):
        key: bytes = PRep.make_key(prep.address)
        value: bytes = prep.to_bytes()
        self._db.put(context, key, value)

    def delete_prep(self, context: 'IconScoreContext', address: 'Address'):
        key: bytes = PRep.make_key(address)
        self._db.delete(context, key)

    def get_prep_iterator(self) -> iter:
        with self._db.key_value_db.get_sub_db(PRep.PREFIX).iterator() as it:
            for _, value in it:
                yield PRep.from_bytes(value)

    def put_term(self, context: 'IconScoreContext', data: list):
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.TERM_KEY, value)

    def get_term(self, context: 'IconScoreContext') -> Optional[list]:
        value: bytes = self._db.get(context, self.TERM_KEY)
        if value:
            return MsgPackForDB.loads(value)
        return None
