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

from typing import TYPE_CHECKING, Optional, Iterable

from .data import Term
from .data.prep import PRep
from ..base.ComponentBase import StorageBase
from ..base.exception import InvalidParamsException
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.db import ContextDatabase


class Storage(StorageBase):
    PREFIX: bytes = b'prep'
    TERM_KEY: bytes = PREFIX + b'term'
    PREP_REGISTRATION_FEE_KEY: bytes = PREFIX + b'prf'

    def __init__(self, db: 'ContextDatabase'):
        super().__init__(db)
        self.prep_registration_fee: Optional[int] = None

    def open(self,
             context: 'IconScoreContext',
             prep_registration_fee: int):

        prep_reg_fee_from_db: Optional[int] = self.get_prep_registration_fee(context)
        if prep_reg_fee_from_db is None:
            self.put_prep_registration_fee(context, prep_registration_fee)
            self.prep_registration_fee = prep_registration_fee
        else:
            self.prep_registration_fee = prep_reg_fee_from_db

    def get_prep_registration_fee(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.PREP_REGISTRATION_FEE_KEY)
        if value:
            data = MsgPackForDB.loads(value)
            version: int = data[0]
            assert version == 0
            prep_reg_fee: int = data[1]
            return prep_reg_fee
        else:
            return None

    def put_prep_registration_fee(self, context: 'IconScoreContext', prep_reg_fee: int):
        version = 0
        data: bytes = MsgPackForDB.dumps([version, prep_reg_fee])
        self._db.put(context, self.PREP_REGISTRATION_FEE_KEY, data)

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
        value: bytes = prep.to_bytes(context.revision)
        self._db.put(context, key, value)

    def delete_prep(self, context: 'IconScoreContext', address: 'Address'):
        key: bytes = PRep.make_key(address)
        self._db.delete(context, key)

    def get_prep_iterator(self) -> Iterable['PRep']:
        with self._db.key_value_db.get_sub_db(PRep.PREFIX).iterator() as it:
            for key, value in it:
                if key[0] == 0x00 and len(key) == 21:
                    yield PRep.from_bytes(value)

    def put_term(self, context: 'IconScoreContext', term: 'Term'):
        value: bytes = MsgPackForDB.dumps(term.to_list())
        self._db.put(context, self.TERM_KEY, value)

    def get_term(self,
                 context: 'IconScoreContext') -> Optional['Term']:

        value: bytes = self._db.get(context, self.TERM_KEY)
        if value:
            total_elected_prep_delegated_snapshot: int = \
                context.storage.rc.get_total_elected_prep_delegated_snapshot()
            data: list = MsgPackForDB.loads(value)
            return Term.from_list(data,
                                  context.block.height,
                                  total_elected_prep_delegated_snapshot)
