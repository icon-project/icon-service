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

from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..base.type_converter_templates import ConstantKeys
from ..utils.msgpack_for_db import MsgPackForDB


class Candidate(object):
    """PrepCandidate Register Info class
    Contains information of the PrepCandidate indicated by address.
    """

    _VERSION = 0
    prefix = b'prepri'

    def __init__(self, address: 'Address') -> None:
        """Constructor
        """
        # key
        self.address: 'Address' = address

        # value
        self.public_key: str = ""
        self.name: str = ""
        self.email: str = ""
        self.website: str = ""
        self.json: str = ""
        self.url: str = ""
        self.block_height: int = 0
        self.tx_index: int = 0
        self.gv: 'GovernanceVariables' = GovernanceVariables()

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        return Candidate.prefix + Address.to_bytes_including_prefix(address)

    def to_bytes(self) -> bytes:
        """Convert PrepCandidate object to bytes

        :return: data including information of PrepCandidate object
        """

        data = [
            self._VERSION,
            self.public_key,
            self.name,
            self.email,
            self.website,
            self.json,
            self.url,
            self.block_height,
            self.tx_index,
            self.gv.encode()
        ]
        return MsgPackForDB.dumps(data)

    @staticmethod
    def from_bytes(data: bytes, address: 'Address') -> 'Candidate':
        """Create PrepCandidate object from bytes data

        :param address:
        :param data: (bytes) bytes data including PrepCandidate information
        :return: (PrepCandidate) PrepCandidate object
        """

        data_list: list = MsgPackForDB.loads(data)
        version: int = data_list[0]

        assert version == Candidate._VERSION

        if version != Candidate._VERSION:
            raise InvalidParamsException(f"Invalid PrepCandidate version: {version}")

        obj: 'Candidate' = Candidate(address)
        obj.public_key: bytes = data_list[1]
        obj.name: str = data_list[2]
        obj.email: str = data_list[3]
        obj.website: str = data_list[4]
        obj.json: str = data_list[5]
        obj.url: str = data_list[6]
        obj.block_height: int = data_list[7]
        obj.tx_index: int = data_list[8]
        obj.gv: 'GovernanceVariables' = GovernanceVariables.decode(data_list[9])
        return obj

    @staticmethod
    def from_dict(data: dict, block_height: int, tx_index: int, address: 'Address') -> 'Candidate':
        obj: 'Candidate' = Candidate(address)
        obj.public_key: bytes = data.get(ConstantKeys.PUBLIC_KEY, b'')
        obj.name: str = data.get(ConstantKeys.NAME, "")
        obj.email: str = data.get(ConstantKeys.EMAIL, "")
        obj.website: str = data.get(ConstantKeys.WEBSITE, "")
        obj.json: str = data.get(ConstantKeys.JSON, "")
        obj.url: str = data.get(ConstantKeys.URL, "")
        gv: dict = data.get(ConstantKeys.GOVERNANCE_VARIABLE, {})
        obj.gv.incentiveRep: int = gv.get(ConstantKeys.INCENTIVE_REP, 0)
        obj.block_height: int = block_height
        obj.tx_index: int = tx_index
        return obj

    def update_dict(self, data: dict):
        self.name: str = data.get(ConstantKeys.NAME, self.name)
        self.email: str = data.get(ConstantKeys.EMAIL, self.email)
        self.website: str = data.get(ConstantKeys.WEBSITE, self.website)
        self.json: str = data.get(ConstantKeys.JSON, self.json)
        self.url: str = data.get(ConstantKeys.URL, self.url)
        gv: dict = data.get(ConstantKeys.GOVERNANCE_VARIABLE)
        if gv:
            self.gv.incentiveRep: int = \
                gv.get(ConstantKeys.INCENTIVE_REP, self.gv.incentiveRep)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (PrepCandidate)
        """
        return isinstance(other, Candidate) \
               and self.address == other.address \
               and self.name == other.name \
               and self.email == other.email \
               and self.website == other.website \
               and self.json == other.json \
               and self.url == other.url \
               and self.block_height == other.block_height \
               and self.tx_index == other.tx_index \
               and self.gv == other.gv

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (PrepCandidate)
        """
        return not self.__eq__(other)


class GovernanceVariables(object):
    _VERSION = 0

    def __init__(self):
        self.incentiveRep: int = 0

    def encode(self) -> list:
        data = [
            self._VERSION,
            self.incentiveRep
        ]
        return data

    @staticmethod
    def decode(data: list) -> 'GovernanceVariables':
        obj = GovernanceVariables()
        version: int = data[0]
        obj.incentiveRep: int = data[1]
        return obj

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (GovernanceVariables)
        """
        return isinstance(other, GovernanceVariables) \
            and self.incentiveRep == other.incentiveRep

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (GovernanceVariables)
        """
        return not self.__eq__(other)
