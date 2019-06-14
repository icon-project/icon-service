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

from typing import TYPE_CHECKING, Optional, List

from .data.candidate import Candidate
from ..base.ComponentBase import StorageBase
from ..base.exception import InvalidParamsException
from ..base.type_converter_templates import ConstantKeys
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    PREFIX: bytes = b'prep'
    GOVERNANCE_VARIABLE_KEY: bytes = PREFIX + b'gv'
    PREPS_KEY: bytes = PREFIX + b'preps'

    def open(self, context: 'IconScoreContext', governance_variable: dict):
        if self.get_gv(context) is None:
            gv: 'GovernanceVariable' = GovernanceVariable.from_config_data(governance_variable)
            if gv.incentive_rep <= 0:
                raise Exception
            self.put_gv(context, gv)

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

    def put_gv(self, context: 'IconScoreContext', gv: 'GovernanceVariable'):
        self._db.put(context, self.GOVERNANCE_VARIABLE_KEY, gv.to_bytes())

    def get_gv(self, context: 'IconScoreContext') -> Optional['GovernanceVariable']:
        value: bytes = self._db.get(context, self.GOVERNANCE_VARIABLE_KEY)
        if value:
            return GovernanceVariable.from_bytes(value)
        return None

    def put_preps(self, context: 'IconScoreContext', preps: 'PReps'):
        self._db.put(context, self.PREPS_KEY, preps.to_bytes())

    def get_preps(self, context: 'IconScoreContext') -> Optional['PReps']:
        value: bytes = self._db.get(context, self.PREPS_KEY)
        if value:
            return PReps.from_bytes(value)
        return None


class GovernanceVariable(object):
    _VERSION = 0

    def __init__(self):
        self.incentive_rep: int = 0

    @staticmethod
    def from_bytes(buf: bytes) -> 'GovernanceVariable':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        obj = GovernanceVariable()
        obj.incentive_rep: int = data[1]
        return obj

    @staticmethod
    def from_config_data(data: dict) -> 'GovernanceVariable':
        obj = GovernanceVariable()
        obj.incentive_rep: int = data[ConstantKeys.INCENTIVE_REP]
        return obj

    def to_bytes(self) -> bytes:
        """Convert GovernanceVariable object to bytes

        :return: data including information of GovernanceVariable object
        """

        data = [
            self._VERSION,
            self.incentive_rep
        ]
        return MsgPackForDB.dumps(data)


class PReps(object):
    _VERSION = 0

    def __init__(self):
        self.preps: List['PRep'] = []

    @staticmethod
    def from_bytes(buf: bytes) -> 'PReps':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        obj = PReps()
        for prep in data[1:]:
            obj.preps.append(PRep.from_list(prep))
        return obj

    @staticmethod
    def from_list(preps: list) -> 'PReps':
        obj = PReps()

        for p in preps:
            prep: 'PRep' = PRep(p.address, p.delegated)
            obj.preps.append(prep)
        return obj

    def to_bytes(self) -> bytes:
        data = [
            self._VERSION
        ]
        for prep in self.preps:
            data.append(prep.to_list())
        return MsgPackForDB.dumps(data)


class PRep(object):
    _VERSION = 0

    def __init__(self, address: 'Address', delegated: int):
        self.address: 'Address' = address
        self.delegated: int = delegated

    @staticmethod
    def from_list(data: list) -> 'PRep':
        version = data[0]

        obj = PRep(data[1], data[2])
        return obj

    def to_list(self) -> list:
        data = [
            self._VERSION,
            self.address,
            self.delegated
        ]
        return data


