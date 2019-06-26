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

from ...base.exception import InvalidParamsException
from ...base.type_converter_templates import ConstantKeys
from ...icon_constant import PRepStatus, PREP_STATUS_MAPPER, PENALTY_GRACE_PERIOD, MIN_PRODUCTIVITY_PERCENTAGE
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from iconservice.base.address import Address


class PRepFlag(Flag):
    NONE = 0
    DIRTY = auto()
    READONLY = auto()


class PRep(object):
    PREFIX: bytes = b"prep"
    _VERSION: int = 0

    class Index(IntEnum):
        VERSION = 0
        ADDRESS = auto()

        STATUS = auto()
        NAME = auto()
        EMAIL = auto()
        WEBSITE = auto()
        DETAILS = auto()
        P2P_END_POINT = auto()
        PUBLIC_KEY = auto()
        IREP = auto()
        IREP_BLOCK_HEIGHT = auto()

        BLOCK_HEIGHT = auto()
        TX_INDEX = auto()

        TOTAL_BLOCKS = auto()
        VALIDATE_BLOCKS = auto()

        SIZE = auto()

    def __init__(self, address: 'Address', flags: 'PRepFlag' = PRepFlag.NONE):
        # flags
        self.flags: 'PRepFlag' = flags

        # key
        self.address: 'Address' = address

        # The delegated amount retrieved from account
        self.stake: int = 0
        self.delegated: int = 0

        # status
        self._status: 'PRepStatus' = PRepStatus.NONE
        # registration info
        self.name: str = ""
        self.email: str = ""
        self.website: str = ""
        self.details: str = ""
        # information required for P-Rep Consensus
        self.public_key: bytes = b""
        self.p2p_end_point: str = ""
        # Governance Variables
        self.irep: int = 0
        self.irep_block_height: int = 0

        # registration time
        self.block_height: int = 0
        self.tx_index: int = 0

        # stats
        self._total_blocks: int = 0
        self._validated_blocks: int = 0

    @property
    def status(self) -> 'PRepStatus':
        return self._status

    @status.setter
    def status(self, value: 'PRepStatus'):
        if value == PRepStatus.ACTIVE and self._status != PRepStatus.NONE:
            raise InvalidParamsException(f"Invalid init status setting: {value}")
        elif value != PRepStatus.ACTIVE and self._status == PRepStatus.NONE:
            raise InvalidParamsException(f"Invalid status setting: {value}")
        self._status = value

    def update_productivity(self, is_validate: bool):
        if is_validate:
            self._validated_blocks += 1
        self._total_blocks += 1

    @property
    def productivity(self):
        # return : % (percentage)
        return self._validated_blocks * 100 // self._total_blocks

    def is_low_productivity(self) -> bool:
        # A grace period without measuring productivity
        if self._total_blocks <= PENALTY_GRACE_PERIOD:
            return False

        return self.productivity < MIN_PRODUCTIVITY_PERCENTAGE

    @classmethod
    def make_key(cls, address: 'Address') -> bytes:
        return cls.PREFIX + address.to_bytes_including_prefix()

    def __gt__(self, other: 'PRep') -> bool:
        return self.order() > other.order()

    def __lt__(self, other: 'PRep') -> bool:
        return self.order() < other.order()

    def order(self) -> Tuple[int, int, int]:
        """Returns tuple used for sorting preps in descending order

        :return: delegated, block_height, tx_index
        """
        return self.delegated, -self.block_height, -self.tx_index

    def to_bytes(self) -> bytes:
        return MsgPackForDB.dumps([
            self._VERSION,

            self._status.value,

            self.name,
            self.email,
            self.website,
            self.details,
            self.p2p_end_point,
            self.public_key,
            self.irep,
            self.irep_block_height,

            self.block_height,
            self.tx_index,

            self._total_blocks,
            self._validated_blocks,
        ])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PRep':
        items: list = MsgPackForDB.loads(data)
        assert len(items) == cls.Index.SIZE

        prep = PRep(items[cls.Index.ADDRESS])

        prep._status = PRepStatus[items[cls.Index.STATUS]]

        prep.name = items[cls.Index.NAME]
        prep.email = items[cls.Index.EMAIL]
        prep.website = items[cls.Index.WEBSITE]
        prep.details = items[cls.Index.DETAILS]
        prep.p2p_end_point = items[cls.Index.P2P_END_POINT]
        prep.public_key = items[cls.Index.PUBLIC_KEY]
        prep.irep = items[cls.Index.IREP]
        prep.irep_block_height = items[cls.Index.IREP_BLOCK_HEIGHT]

        prep.block_height = items[cls.Index.BLOCK_HEIGHT]
        prep.tx_index = items[cls.Index.TX_INDEX]

        prep._total_blocks = items[cls.Index.TOTAL_BLOCKS]
        prep._validated_blocks = items[cls.Index.VALIDATE_BLOCKS]

        return prep

    @staticmethod
    def from_dict(address: 'Address', data: dict, block_height: int, tx_index: int,
                  irep: int) -> 'PRep':
        prep = PRep(address)

        prep._status: int = PRepStatus.ACTIVE

        # Optional items
        prep.name: str = data.get(ConstantKeys.NAME, "")
        prep.email: str = data.get(ConstantKeys.EMAIL, "")
        prep.website: str = data.get(ConstantKeys.WEBSITE, "")
        prep.details: str = data.get(ConstantKeys.DETAILS, "")

        # Required items
        prep.p2p_end_point: str = data[ConstantKeys.P2P_END_POINT]
        prep.public_key: bytes = data[ConstantKeys.PUBLIC_KEY]
        prep.irep: int = irep
        prep.irep_block_height: int = block_height

        # Registration time
        prep.block_height: int = block_height
        prep.tx_index: int = tx_index

        return prep

    def set(self, params: dict, block_height: int):
        # Optional items
        self.name: str = params.get(ConstantKeys.NAME, self.name)
        self.email: str = params.get(ConstantKeys.EMAIL, self.email)
        self.website: str = params.get(ConstantKeys.WEBSITE, self.website)
        self.details: str = params.get(ConstantKeys.DETAILS, self.details)

        # Required items
        self.p2p_end_point: str = params.get(ConstantKeys.P2P_END_POINT, self.p2p_end_point)

        if ConstantKeys.IREP in params and self.irep != params[ConstantKeys.IREP]:
            self.irep: int = params[ConstantKeys.IREP]
            self.irep_block_height: int = block_height

    def to_dict(self) -> dict:
        return {
            "status": PREP_STATUS_MAPPER[self.status],
            "registration": {
                ConstantKeys.NAME: self.name,
                ConstantKeys.EMAIL: self.email,
                ConstantKeys.WEBSITE: self.website,
                ConstantKeys.DETAILS: self.details,
                ConstantKeys.P2P_END_POINT: self.p2p_end_point,
                ConstantKeys.PUBLIC_KEY: self.public_key,
                ConstantKeys.IREP: self.irep,
                ConstantKeys.IREP_BLOCK_HEIGHT: self.irep_block_height
            },
            "delegation": {
                "stake": self.stake,
                "delegated": self.delegated
            },
            "stats": {
                "totalBlocks": self._total_blocks,
                "validatedBlocks": self._validated_blocks
            }
        }
