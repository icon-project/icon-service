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

import copy
from enum import auto, Flag, IntEnum
from typing import TYPE_CHECKING, Tuple

from .sorted_list import Sortable
from ... import utils
from ...base.exception import AccessDeniedException, InvalidParamsException
from ...base.type_converter_templates import ConstantKeys
from ...icon_constant import PRepStatus, PREP_STATUS_MAPPER, PENALTY_GRACE_PERIOD, MIN_PRODUCTIVITY_PERCENTAGE
from ...utils.msgpack_for_db import MsgPackForDB
from ...icon_constant import IISS_MIN_IREP

if TYPE_CHECKING:
    from iconservice.base.address import Address


class PRepFlag(Flag):
    NONE = 0
    DIRTY = auto()
    FROZEN = auto()


class PRep(Sortable):
    PREFIX: bytes = b"prep"
    _VERSION: int = 0

    class Index(IntEnum):
        VERSION = 0

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
        VALIDATED_BLOCKS = auto()

        SIZE = auto()

    def __init__(
            self, address: 'Address',
            *,
            flags: 'PRepFlag' = PRepFlag.NONE,
            status: 'PRepStatus' = PRepStatus.ACTIVE,
            name: str = "",
            email: str = "",
            website: str = "",
            details: str = "",
            p2p_end_point: str = "",
            public_key: bytes = b"",
            irep: int = 0,
            irep_block_height: int = 0,
            stake: int = 0,
            delegated: int = 0,
            block_height: int = 0,
            tx_index: int = 0,
            total_blocks: int = 0,
            validated_blocks: int = 0):
        """
        Main PRep: top 1 ~ 22 preps in descending order by delegated amount
        Sub PRep: 23 ~ 100 preps
        PRep: All PReps including Main PRep and Sub PRep

        :param address:
        :param flags:
        :param name:
        :param email:
        :param website:
        :param details:
        :param public_key:
        :param p2p_end_point:
        :param irep:
        :param delegated:
        :param block_height:
        :param tx_index:
        """
        assert irep_block_height == block_height

        # key
        self._address: 'Address' = address

        # flags
        self._flags: 'PRepFlag' = flags

        # The delegated amount retrieved from account
        self.stake: int = stake
        self._delegated: int = delegated

        # status
        self._status: 'PRepStatus' = status
        # registration info
        self.name: str = name
        self.email: str = email
        self.website: str = website
        self.details: str = details
        # information required for PRep Consensus
        self._public_key: bytes = public_key
        self.p2p_end_point: str = p2p_end_point
        # Governance Variables
        self.irep: int = irep
        self.irep_block_height: int = irep_block_height

        # registration time
        self._block_height: int = block_height
        self._tx_index: int = tx_index

        # stats
        self._total_blocks: int = total_blocks
        self._validated_blocks: int = validated_blocks

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
    def productivity(self) -> int:
        # return : % (percentage)
        return self._validated_blocks * 100 // self._total_blocks

    def is_low_productivity(self) -> bool:
        # A grace period without measuring productivity
        if self._total_blocks <= PENALTY_GRACE_PERIOD:
            return False

        return self.productivity < MIN_PRODUCTIVITY_PERCENTAGE

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def delegated(self) -> int:
        return self._delegated

    @delegated.setter
    def delegated(self, value: int):
        if self.is_frozen():
            raise AccessDeniedException("P-Rep is frozen")

        self._delegated = value

    @property
    def public_key(self) -> bytes:
        return self._public_key

    @property
    def block_height(self) -> int:
        return self._block_height

    @property
    def tx_index(self) -> int:
        return self._tx_index

    @classmethod
    def make_key(cls, address: 'Address') -> bytes:
        return cls.PREFIX + address.to_bytes_including_prefix()

    def is_flag_on(self, flags: 'PRepFlag') -> bool:
        return bool(self._flags & flags == flags)

    def toggle_flag(self, flags: PRepFlag, on: bool):
        """Toggle flags
        This method should be called only by PRepContainer

        :param flags:
        :param on:
        :return:
        """
        utils.toggle_flags(self._flags, flags, on)

    def is_frozen(self) -> bool:
        return bool(self._flags & PRepFlag.FROZEN)

    def freeze(self):
        """Make all member variables immutable

        :return:
        """
        self._flags |= PRepFlag.FROZEN

    def set(self, block_height: int, *,
            name: str = None,
            email: str = None,
            website: str = None,
            details: str = None,
            p2p_end_point: str = None,
            irep: int = None):
        """Update PRep properties on processing setPRep JSON-RPC API

        Not allowed to update some properties which can affect PRep order or are immutable

        :param name:
        :param email:
        :param website:
        :param details:
        :param p2p_end_point:
        :param irep:
        :param irep_block_height: Block height when irep is updated
        """
        if self.is_frozen():
            raise AccessDeniedException("P-Rep access denied")

        irep_block_height: int = None if irep is None else block_height
        assert (irep is None and block_height is None) or \
            (isinstance(irep, int) and isinstance(irep_block_height, int))

        kwargs = {
            "name": name,
            "email": email,
            "website": website,
            "details": details,
            "p2p_end_point": p2p_end_point,
            "irep": irep,
            "irep_block_height": irep_block_height
        }

        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

        self._flags |= PRepFlag.DIRTY

    def __gt__(self, other: 'PRep') -> bool:
        return self.order() > other.order()

    def __lt__(self, other: 'PRep') -> bool:
        return self.order() < other.order()

    def order(self) -> Tuple[int, int, int]:
        """Returns tuple used for sorting preps in descending order

        :return: delegated, block_height, tx_index
        """
        return -self._delegated, self._block_height, self._tx_index

    def to_bytes(self) -> bytes:
        return MsgPackForDB.dumps([
            self._VERSION,
            self.address,
            self.status.value,
            self.name,
            self.email,
            self.website,
            self.details,
            self.p2p_end_point,
            self._public_key,

            self.irep,
            self.irep_block_height,

            self._block_height,
            self._tx_index,

            self._total_blocks,
            self._validated_blocks,
        ])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PRep':
        items: list = MsgPackForDB.loads(data)
        assert len(items) == cls.Index.SIZE

        return PRep(
            address=items[cls.Index.ADDRESS],
            status=PRepStatus(items[cls.Index.STATUS]),
            name=items[cls.Index.NAME],
            email=items[cls.Index.EMAIL],
            website=items[cls.Index.WEBSITE],
            details=items[cls.Index.DETAILS],
            p2p_end_point=items[cls.Index.P2P_END_POINT],
            public_key=items[cls.Index.PUBLIC_KEY],
            irep=items[cls.Index.IREP],
            irep_block_height=items[cls.Index.IREP_BLOCK_HEIGHT],
            block_height=items[cls.Index.BLOCK_HEIGHT],
            tx_index=items[cls.Index.TX_INDEX],
            total_blocks=items[cls.Index.TOTAL_BLOCKS],
            validated_blocks=items[cls.Index.VALIDATED_BLOCKS]
        )

    @staticmethod
    def from_dict(address: 'Address', data: dict, block_height: int, tx_index: int) -> 'PRep':
        """Create a PRep instance from data included in registerPRep JSON-RPC request

        :param address:
        :param data:
        :param block_height:
        :param tx_index:
        :return:
        """
        return PRep(
            flags=PRepFlag.NONE,
            address=address,
            status=PRepStatus.ACTIVE,

            # Optional items
            name=data.get(ConstantKeys.NAME, ""),
            email=data.get(ConstantKeys.EMAIL, ""),
            website=data.get(ConstantKeys.WEBSITE, ""),
            details=data.get(ConstantKeys.DETAILS, ""),

            # Required items
            p2p_end_point=data[ConstantKeys.P2P_END_POINT],
            public_key=data[ConstantKeys.PUBLIC_KEY],
            irep=IISS_MIN_IREP,
            irep_block_height=block_height,

            # Registration time
            block_height=block_height,
            tx_index=tx_index
        )

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
                "delegated": self._delegated
            },
            "stats": {
                "totalBlocks": self._total_blocks,
                "validatedBlocks": self._validated_blocks
            }
        }

    def __str__(self) -> str:
        return str(self.to_dict())

    def copy(self, flags: 'PRepFlag' = PRepFlag.NONE) -> 'PRep':
        prep = copy.copy(self)
        prep._flags = flags

        return prep
