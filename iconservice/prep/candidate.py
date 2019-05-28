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

from operator import lt, gt
from typing import TYPE_CHECKING

from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..base.type_converter_templates import ConstantKeys
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address


class _DBPart(object):
    """Candidate Register Info class
    Contains information of the Candidate indicated by address.
    """

    _VERSION = 0
    prefix = b'prepri'

    def __init__(self,
                 name: str = "",
                 email: str = "",
                 website: str = "",
                 json: str = "",
                 ip: str = "",
                 block_height: int = 0,
                 tx_index: int = 0,
                 incentive_rep: int = 0):
        """Constructor
        """

        # value
        self.name: str = name
        self.email: str = email
        self.website: str = website
        self.json: str = json
        self.ip: str = ip
        self.block_height: int = block_height
        self.tx_index: int = tx_index
        self.gv: 'GovernanceVariables' = GovernanceVariables()
        self.gv.incentive_rep: int = incentive_rep

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        return _DBPart.prefix + Address.to_bytes_including_prefix(address)

    def to_bytes(self) -> bytes:
        """Convert PrepCandidate object to bytes

        :return: data including information of PrepCandidate object
        """

        data = [
            self._VERSION,
            self.name,
            self.email,
            self.website,
            self.json,
            self.ip,
            self.block_height,
            self.tx_index,
            self.gv.encode()
        ]
        return MsgPackForDB.dumps(data)

    @staticmethod
    def from_bytes(data: bytes) -> '_DBPart':
        """Create PrepCandidate object from bytes data

        :param data: (bytes) bytes data including PrepCandidate information
        :return: (PrepCandidate) PrepCandidate object
        """

        data_list: list = MsgPackForDB.loads(data)
        version: int = data_list[0]

        assert version == _DBPart._VERSION

        if version != _DBPart._VERSION:
            raise InvalidParamsException(f"Invalid Candidate version: {version}")

        obj: '_DBPart' = _DBPart()
        obj.name: str = data_list[1]
        obj.email: str = data_list[2]
        obj.website: str = data_list[3]
        obj.json: str = data_list[4]
        obj.ip: str = data_list[5]
        obj.block_height: int = data_list[6]
        obj.tx_index: int = data_list[7]
        obj.gv: 'GovernanceVariables' = GovernanceVariables.decode(data_list[8])
        return obj

    @staticmethod
    def from_dict(data: dict, block_height: int, tx_index: int) -> '_DBPart':
        obj: '_DBPart' = _DBPart()
        obj.name: str = data[ConstantKeys.NAME]
        obj.email: str = data[ConstantKeys.EMAIL]
        obj.website: str = data[ConstantKeys.WEBSITE]
        obj.json: str = data[ConstantKeys.JSON]
        obj.ip: str = data[ConstantKeys.IP]
        gv: dict = data[ConstantKeys.GOVERNANCE_VARIABLE]
        obj.gv.incentive_rep: int = gv[ConstantKeys.INCENTIVE_REP]
        obj.block_height: int = block_height
        obj.tx_index: int = tx_index
        return obj

    def update_dict(self, data: dict):
        self.name: str = data.get(ConstantKeys.NAME, self.name)
        self.email: str = data.get(ConstantKeys.EMAIL, self.email)
        self.website: str = data.get(ConstantKeys.WEBSITE, self.website)
        self.json: str = data.get(ConstantKeys.JSON, self.json)
        self.ip: str = data.get(ConstantKeys.IP, self.ip)
        gv: dict = data.get(ConstantKeys.GOVERNANCE_VARIABLE)
        if gv:
            self.gv.incentive_rep: int = \
                gv.get(ConstantKeys.INCENTIVE_REP, self.gv.incentive_rep)

    def __eq__(self, other: '_DBPart') -> bool:
        """operator == overriding

        :param other: (_DBPart)
        """
        return isinstance(other, _DBPart) \
               and self.name == other.name \
               and self.email == other.email \
               and self.website == other.website \
               and self.json == other.json \
               and self.ip == other.ip \
               and self.block_height == other.block_height \
               and self.tx_index == other.tx_index \
               and self.gv == other.gv

    def __ne__(self, other: '_DBPart') -> bool:
        """operator != overriding

        :param other: (_DBPart)
        """
        return not self.__eq__(other)


class GovernanceVariables(object):
    _VERSION = 0

    def __init__(self):
        self.incentive_rep: int = 0

    def encode(self) -> list:
        data = [
            self._VERSION,
            self.incentive_rep
        ]
        return data

    @staticmethod
    def decode(data: list) -> 'GovernanceVariables':
        obj = GovernanceVariables()
        version: int = data[0]
        obj.incentive_rep: int = data[1]
        return obj

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (GovernanceVariables)
        """
        return isinstance(other, GovernanceVariables) \
               and self.incentive_rep == other.incentive_rep

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (GovernanceVariables)
        """
        return not self.__eq__(other)


class Candidate(object):
    prefix: bytes = _DBPart.prefix

    def __init__(self,
                 address: 'Address',
                 name: str = "",
                 email: str = "",
                 website: str = "",
                 json: str = "",
                 ip: str = "",
                 block_height: int = 0,
                 tx_index: int = 0,
                 incentive_rep: int = 0):
        self._address: 'Address' = address
        self._db_part: '_DBPart' = _DBPart(name,
                                           email,
                                           website,
                                           json,
                                           ip,
                                           block_height,
                                           tx_index,
                                           incentive_rep)
        self._total_delegated: int = 0

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def name(self) -> str:
        return self._db_part.name

    @property
    def email(self) -> str:
        return self._db_part.email

    @property
    def website(self) -> str:
        return self._db_part.website

    @property
    def json(self) -> str:
        return self._db_part.json

    @property
    def ip(self) -> str:
        return self._db_part.ip

    @property
    def block_height(self) -> int:
        return self._db_part.block_height

    @property
    def tx_index(self) -> int:
        return self._db_part.tx_index

    @property
    def gv(self) -> 'GovernanceVariables':
        return self._db_part.gv

    @property
    def total_delegated(self) -> int:
        return self._total_delegated

    def update(self, total_delegated: int):
        self._total_delegated: int = total_delegated

    def update_dict(self, data: dict):
        self._db_part.update_dict(data)

    def __eq__(self, other: 'Candidate') -> bool:
        return isinstance(other, Candidate) \
               and self.address == other.address \
               and self._db_part == other._db_part \
               and self.total_delegated == other.total_delegated

    def __ne__(self, other: 'Candidate') -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: 'Candidate') -> bool:
        x: list = self._to_order_list()
        y: list = other._to_order_list()
        is_reverse: list = [False, True, True]

        for i in range(len(x)):
            first_operator = gt
            second_operator = lt

            if is_reverse[i]:
                first_operator = lt
                second_operator = gt

            if first_operator(x[i], y[i]):
                return True
            elif second_operator(x[i], y[i]):
                return False
            else:
                if i != len(x):
                    continue
                else:
                    return False

    def __lt__(self, other: 'Candidate') -> bool:
        return not self.__gt__(other)

    def _to_order_list(self) -> list:
        return [self._total_delegated, self._db_part.block_height, self._db_part.tx_index]

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        return _DBPart.make_key(address)

    def to_bytes(self) -> bytes:
        return self._db_part.to_bytes()

    @staticmethod
    def from_bytes(address: 'Address', data: bytes) -> 'Candidate':
        db_part: '_DBPart' = _DBPart.from_bytes(data)
        return Candidate(address,
                         db_part.name,
                         db_part.email,
                         db_part.website,
                         db_part.json,
                         db_part.ip,
                         db_part.block_height,
                         db_part.tx_index,
                         db_part.gv.incentive_rep)

    @staticmethod
    def from_dict(address: 'Address', data: dict, block_height: int, tx_index: int) -> 'Candidate':
        db_part: '_DBPart' = _DBPart.from_dict(data, block_height, tx_index)
        return Candidate(address,
                         db_part.name,
                         db_part.email,
                         db_part.website,
                         db_part.json,
                         db_part.ip,
                         db_part.block_height,
                         db_part.tx_index,
                         db_part.gv.incentive_rep)
