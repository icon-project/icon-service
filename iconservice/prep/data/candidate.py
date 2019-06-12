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

from enum import auto, Flag, IntEnum
from typing import TYPE_CHECKING, Tuple

from ...base.address import Address
from ...base.type_converter_templates import ConstantKeys
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from iconservice.base.address import Address


class CandidateFlag(Flag):
    NONE = 0
    DIRTY = auto()
    READONLY = auto()


class RegPart(object):
    """Defines registration info of a P-Rep Candidate

    """

    def __init__(self):
        # registration time
        self.block_height: int = 0
        self.tx_index: int = 0

        # registration info
        self.name: str = ""
        self.email: str = ""
        self.website: str = ""
        self.details: str = ""
        # information required for P-Rep Consensus
        self.public_key: bytes = b""
        self.p2p_end_point: str = ""
        # Governance Variables
        self.incentive_rep: int = 0


class Candidate(object):
    PREFIX: bytes = b"candidate"
    _VERSION: int = 0

    class Index(IntEnum):
        VERSION = 0
        ADDRESS = auto()
        NAME = auto()
        EMAIL = auto()
        WEBSITE = auto()
        DETAILS = auto()
        P2P_END_POINT = auto()
        PUBLIC_KEY = auto()
        INCENTIVE_REP = auto()
        BLOCK_HEIGHT = auto()
        TX_INDEX = auto()

        SIZE = auto()

    def __init__(self, address: 'Address', flags: 'CandidateFlag' = CandidateFlag.NONE):
        # flags
        self.flags: 'CandidateFlag' = flags

        # key
        self.address: 'Address' = address

        # registration time
        self.block_height: int = 0
        self.tx_index: int = 0

        # The delegated amount retrieved from account
        self.delegated: int = 0

        # registration info
        self.name: str = ""
        self.email: str = ""
        self.website: str = ""
        self.details: str = ""
        # information required for P-Rep Consensus
        self.public_key: bytes = b""
        self.p2p_end_point: str = ""
        # Governance Variables
        self.incentive_rep: int = 0

    @classmethod
    def make_key(cls, address: 'Address') -> bytes:
        return cls.PREFIX + address.to_bytes_including_prefix()

    def set(self, params: dict):
        # Optional items
        self.name: str = params.get(ConstantKeys.NAME, self.name)
        self.email: str = params.get(ConstantKeys.EMAIL, self.email)
        self.website: str = params.get(ConstantKeys.WEBSITE, self.website)
        self.details: str = params.get(ConstantKeys.DETAILS, self.details)

        # Required items
        self.p2p_end_point: str = params.get(ConstantKeys.P2P_END_POINT, self.p2p_end_point)
        self.public_key: bytes = params.get(ConstantKeys.PUBLIC_KEY, self.public_key)

        gv: dict = params.get(ConstantKeys.GOVERNANCE_VARIABLE)
        if gv is not None:
            self.incentive_rep: int = gv.get(ConstantKeys.INCENTIVE_REP, self.incentive_rep)

    def __gt__(self, other: 'Candidate') -> bool:
        return self.order() > other.order()

    def __lt__(self, other: 'Candidate') -> bool:
        return self.order() < other.order()

    def order(self) -> Tuple[int, int, int]:
        """Returns tuple used for sorting candidates in descending order

        :return: delegated, block_height, tx_index
        """
        return self.delegated, self.block_height, self.tx_index

    def to_bytes(self) -> bytes:
        return MsgPackForDB.dumps([
            self._VERSION,
            self.name,
            self.email,
            self.website,
            self.details,
            self.p2p_end_point,
            self.public_key,
            self.incentive_rep,
            self.block_height,
            self.tx_index,
        ])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Candidate':
        items: list = MsgPackForDB.loads(data)
        assert len(items) == cls.Index.SIZE

        candidate = Candidate(items[cls.Index.ADDRESS])
        candidate.name = items[cls.Index.NAME]
        candidate.email = items[cls.Index.EMAIL]
        candidate.website = items[cls.Index.WEBSITE]
        candidate.details = items[cls.Index.DETAILS]
        candidate.p2p_end_point = items[cls.Index.P2P_END_POINT]
        candidate.public_key = items[cls.Index.PUBLIC_KEY]
        candidate.incentive_rep = items[cls.Index.INCENTIVE_REP]
        candidate.block_height = items[cls.Index.BLOCK_HEIGHT]
        candidate.tx_index = items[cls.Index.TX_INDEX]

        return candidate

    @staticmethod
    def from_dict(address: 'Address', data: dict, block_height: int, tx_index: int) -> 'Candidate':
        candidate = Candidate(address)

        # Optional items
        candidate.name: str = data.get(ConstantKeys.NAME, "")
        candidate.email: str = data.get(ConstantKeys.EMAIL, "")
        candidate.website: str = data.get(ConstantKeys.WEBSITE, "")
        candidate.details: str = data.get(ConstantKeys.DETAILS, "")

        # Required items
        candidate.p2p_end_point: str = data[ConstantKeys.P2P_END_POINT]
        candidate.public_key: bytes = data[ConstantKeys.PUBLIC_KEY]
        candidate.incentive_rep: int = data[ConstantKeys.GOVERNANCE_VARIABLE][ConstantKeys.INCENTIVE_REP]

        # Registration time
        candidate.block_height: int = block_height
        candidate.tx_index: int = tx_index

        return candidate

    def to_dict(self) -> dict:
        """Used for the result of getPRepCandidate JSON-RPC API

        :return:
        """
        return {
            ConstantKeys.NAME: self.name,
            ConstantKeys.EMAIL: self.email,
            ConstantKeys.WEBSITE: self.website,
            ConstantKeys.DETAILS: self.details,
            ConstantKeys.PUBLIC_KEY: self.public_key,
            ConstantKeys.P2P_END_POINT: self.p2p_end_point,
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: self.incentive_rep
            }
        }

    def __str__(self) -> str:
        return str(self.to_dict())
