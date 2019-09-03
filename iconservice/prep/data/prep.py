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
from enum import auto, Flag, IntEnum, Enum
from typing import TYPE_CHECKING, Tuple

import iso3166

from .sorted_list import Sortable
from ... import utils
from ...base.exception import AccessDeniedException, InvalidParamsException
from ...base.type_converter_templates import ConstantKeys
from ...icon_constant import PRepGrade, PRepStatus, PenaltyReason, REV_IISS, REV_DECENTRALIZATION
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from iconservice.base.address import Address


class PRepFlag(Flag):
    NONE = 0
    DIRTY = auto()
    FROZEN = auto()


class PRepDictType(Enum):
    FULL = auto()  # getPRep
    ABRIDGED = auto()  # getPReps


class PRep(Sortable):
    PREFIX: bytes = b"prep"
    _VERSION: int = 1
    _UNKNOWN_COUNTRY = iso3166.Country(u"Unknown", "ZZ", "ZZZ", "000", u"Unknown")

    class Index(IntEnum):
        VERSION = 0

        # Version: 0
        ADDRESS = auto()
        STATUS = auto()
        GRADE = auto()
        NAME = auto()
        COUNTRY = auto()
        CITY = auto()
        EMAIL = auto()
        WEBSITE = auto()
        DETAILS = auto()
        P2P_ENDPOINT = auto()
        IREP = auto()
        IREP_BLOCK_HEIGHT = auto()
        LAST_GENERATE_BLOCK_HEIGHT = auto()
        BLOCK_HEIGHT = auto()
        TX_INDEX = auto()
        TOTAL_BLOCKS = auto()
        VALIDATED_BLOCKS = auto()

        # Version: 1
        PENALTY = auto()
        UNVALIDATED_SEQUENCE_BLOCKS = auto()

        # Unused
        SIZE = auto()

    def __init__(
            self, address: 'Address',
            *,
            flags: 'PRepFlag' = PRepFlag.NONE,
            status: 'PRepStatus' = PRepStatus.ACTIVE,
            penalty: 'PenaltyReason' = PenaltyReason.NONE,
            grade: 'PRepGrade' = PRepGrade.CANDIDATE,
            name: str = "",
            country: str = "",
            city: str = "Unknown",
            email: str = "",
            website: str = "",
            details: str = "",
            p2p_endpoint: str = "",
            irep: int = 0,
            irep_block_height: int = 0,
            last_generate_block_height: int = -1,
            stake: int = 0,
            delegated: int = 0,
            block_height: int = 0,
            tx_index: int = 0,
            total_blocks: int = 0,
            validated_blocks: int = 0,
            unvalidated_sequence_blocks: int = 0):
        """
        Main PRep: top 1 ~ 22 preps in descending order by delegated amount
        Sub PRep: 23 ~ 100 preps
        PRep: All PReps including Main PRep and Sub PRep

        :param address:
        :param flags:
        :param status:
        :param penalty:
        :param grade:
        :param name:
        :param country: alpha3 country code (ISO3166)
        :param city:
        :param email:
        :param website:
        :param details:
        :param p2p_endpoint:
        :param irep:
        :param irep_block_height:
        :param stake:
        :param delegated:
        :param block_height:
        :param tx_index:
        :param total_blocks:
        :param validated_blocks:
        :param unvalidated_sequence_blocks
        """
        assert irep_block_height == block_height

        # key
        self._address: 'Address' = address

        # flags
        self._flags: 'PRepFlag' = flags

        self._stake: int = stake
        self._delegated: int = delegated

        # status
        self._status: 'PRepStatus' = status
        self._penalty: 'PenaltyReason' = penalty
        self._grade: 'PRepGrade' = grade

        # registration info
        self.name: str = name
        self._country: 'iso3166.Country' = self._get_country(country)
        self.city: str = city
        self.email: str = email
        self.website: str = website
        self.details: str = details
        # information required for PRep Consensus
        self.p2p_endpoint: str = p2p_endpoint
        # Governance Variables
        self._irep: int = irep
        self._irep_block_height: int = irep_block_height

        # The height of the last block which a P-Rep generated
        self._last_generate_block_height: int = last_generate_block_height

        # registration time
        self._block_height: int = block_height
        self._tx_index: int = tx_index

        # stats
        self._total_blocks: int = total_blocks
        self._validated_blocks: int = validated_blocks
        self._unvalidated_sequence_blocks: int = unvalidated_sequence_blocks

    def is_dirty(self) -> bool:
        return utils.is_flag_on(self._flags, PRepFlag.DIRTY)

    def _set_dirty(self, on: bool):
        self._flags = utils.set_flag(self._flags, PRepFlag.DIRTY, on)

    @property
    def status(self) -> 'PRepStatus':
        return self._status

    @status.setter
    def status(self, value: 'PRepStatus'):
        self._status = value
        self._set_dirty(True)

    @property
    def penalty(self) -> 'PenaltyReason':
        return self._penalty

    def is_suspended(self) -> bool:
        """The suspended P-Rep  cannot serve as Main P-Rep in the Term

        :return:
        """
        return self._penalty == PenaltyReason.BLOCK_VALIDATION

    @penalty.setter
    def penalty(self, value: 'PenaltyReason'):
        self._penalty = value
        self._set_dirty(True)

    @property
    def grade(self) -> 'PRepGrade':
        """The grade of P-Rep
        0: MAIN
        1: SUB
        2: CANDIDATE

        :return:
        """
        return self._grade

    @grade.setter
    def grade(self, value: 'PRepGrade'):
        self._grade = value
        self._set_dirty(True)

    @property
    def country(self) -> str:
        return self._country.alpha3

    @country.setter
    def country(self, alpha3_country_code: str):
        self._country = self._get_country(alpha3_country_code)
        self._set_dirty(True)

    @classmethod
    def _get_country(cls, alpha3_country_code: str) -> 'iso3166.Country':
        return iso3166.countries_by_alpha3.get(
            alpha3_country_code.upper(), cls._UNKNOWN_COUNTRY)

    def update_block_statistics(self, is_validator: bool):
        """Update the block validation statistics of P-Rep

        :param is_validator: If this P-Rep validates a block, then it is True
        """
        self._check_access_permission()

        self._total_blocks += 1

        if is_validator:
            self._validated_blocks += 1
            self._unvalidated_sequence_blocks = 0
        else:
            self._unvalidated_sequence_blocks += 1

        self._set_dirty(True)

    def reset_block_validation_penalty(self):
        """Reset block validation penalty and
        unvalidated sequence blocks before the next term begins

        :return:
        """
        self._penalty = PenaltyReason.NONE
        self._unvalidated_sequence_blocks = 0

    @property
    def total_blocks(self) -> int:
        return self._total_blocks

    @property
    def validated_blocks(self) -> int:
        return self._validated_blocks

    @property
    def block_validation_proportion(self) -> int:
        """Percent without fraction

        :return:
        """
        if self._total_blocks == 0:
            return 0

        return self._validated_blocks * 100 // self._total_blocks

    @property
    def unvalidated_sequence_blocks(self) -> int:
        return self._unvalidated_sequence_blocks

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def stake(self) -> int:
        return self._stake

    @stake.setter
    def stake(self, value: int):
        assert value >= 0
        self._check_access_permission()
        self._stake = value

    @property
    def delegated(self) -> int:
        return self._delegated

    @delegated.setter
    def delegated(self, value: int):
        assert value >= 0
        self._check_access_permission()
        self._delegated = value

    @property
    def irep(self) -> int:
        return self._irep

    @property
    def irep_block_height(self) -> int:
        return self._irep_block_height

    @property
    def last_generate_block_height(self) -> int:
        return self._last_generate_block_height

    @last_generate_block_height.setter
    def last_generate_block_height(self, value: int):
        assert value >= 0
        self._last_generate_block_height = value
        self._set_dirty(True)

    @property
    def block_height(self) -> int:
        return self._block_height

    @property
    def tx_index(self) -> int:
        return self._tx_index

    @classmethod
    def make_key(cls, address: 'Address') -> bytes:
        return cls.PREFIX + address.to_bytes_including_prefix()

    def is_frozen(self) -> bool:
        return bool(self._flags & PRepFlag.FROZEN)

    def freeze(self):
        """Make all member variables immutable

        :return:
        """
        self._flags |= PRepFlag.FROZEN

    def set(self,
            *,
            name: str = None,
            country: str = None,
            city: str = None,
            email: str = None,
            website: str = None,
            details: str = None,
            p2p_endpoint: str = None):
        """Update PRep properties on processing setPRep JSON-RPC API
        Not allowed to update some properties which can affect PRep order or are immutable

        :param name:
        :param country: alpha3 country code
        :param city:
        :param email:
        :param website:
        :param details:
        :param p2p_endpoint:
        """
        self._check_access_permission()

        kwargs = {
            "name": name,
            "country": country,
            "city": city,
            "email": email,
            "website": website,
            "details": details,
            "p2p_endpoint": p2p_endpoint
        }

        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

        self._set_dirty(True)

    def set_irep(self, irep: int, block_height: int):
        """Set incentive rep

        :param irep:
        :param block_height: block height when irep is set
        :return:
        """
        self._check_access_permission()

        self._irep = irep
        self._irep_block_height = block_height
        self._set_dirty(True)

    def __gt__(self, other: 'PRep') -> bool:
        return self.order() > other.order()

    def __lt__(self, other: 'PRep') -> bool:
        return self.order() < other.order()

    def order(self) -> Tuple[int, int, int]:
        """Returns tuple used for sorting preps in descending order

        :return: delegated, block_height, tx_index
        """
        return -self._delegated, self._block_height, self._tx_index

    def to_bytes(self, revision: int) -> bytes:
        if revision >= REV_DECENTRALIZATION:
            return self._to_bytes_v1()
        elif revision == REV_IISS:
            return self._to_bytes_v0()

    def _to_bytes_v0(self) -> bytes:
        version: int = 0
        return MsgPackForDB.dumps([
            version,
            self.address,
            self.status.value,
            self.grade.value,
            self.name,
            self.country,
            self.city,
            self.email,
            self.website,
            self.details,
            self.p2p_endpoint,

            self._irep,
            self._irep_block_height,

            self._last_generate_block_height,

            self._block_height,
            self._tx_index,

            self._total_blocks,
            self._validated_blocks
        ])

    def _to_bytes_v1(self) -> bytes:
        return MsgPackForDB.dumps([
            self._VERSION,
            self.address,
            self.status.value,
            self.grade.value,
            self.name,
            self.country,
            self.city,
            self.email,
            self.website,
            self.details,
            self.p2p_endpoint,

            self._irep,
            self._irep_block_height,

            self._last_generate_block_height,

            self._block_height,
            self._tx_index,

            self._total_blocks,
            self._validated_blocks,
            self._penalty.value,
            self._unvalidated_sequence_blocks
        ])

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PRep':
        items: list = MsgPackForDB.loads(data)
        assert len(items) == cls.Index.SIZE

        version: int = items[cls.Index.VERSION]
        if version == 0:
            return PRep(
                address=items[cls.Index.ADDRESS],
                status=PRepStatus(items[cls.Index.STATUS]),
                grade=PRepGrade(items[cls.Index.GRADE]),
                name=items[cls.Index.NAME],
                country=items[cls.Index.COUNTRY],
                city=items[cls.Index.CITY],
                email=items[cls.Index.EMAIL],
                website=items[cls.Index.WEBSITE],
                details=items[cls.Index.DETAILS],
                p2p_endpoint=items[cls.Index.P2P_ENDPOINT],
                irep=items[cls.Index.IREP],
                irep_block_height=items[cls.Index.IREP_BLOCK_HEIGHT],
                last_generate_block_height=items[cls.Index.LAST_GENERATE_BLOCK_HEIGHT],
                block_height=items[cls.Index.BLOCK_HEIGHT],
                tx_index=items[cls.Index.TX_INDEX],
                total_blocks=items[cls.Index.TOTAL_BLOCKS],
                validated_blocks=items[cls.Index.VALIDATED_BLOCKS]
            )
        elif version == 1:
            return PRep(
                address=items[cls.Index.ADDRESS],
                status=PRepStatus(items[cls.Index.STATUS]),
                penalty=PenaltyReason(items[cls.Index.PENALTY]),
                grade=PRepGrade(items[cls.Index.GRADE]),
                name=items[cls.Index.NAME],
                country=items[cls.Index.COUNTRY],
                city=items[cls.Index.CITY],
                email=items[cls.Index.EMAIL],
                website=items[cls.Index.WEBSITE],
                details=items[cls.Index.DETAILS],
                p2p_endpoint=items[cls.Index.P2P_ENDPOINT],
                irep=items[cls.Index.IREP],
                irep_block_height=items[cls.Index.IREP_BLOCK_HEIGHT],
                last_generate_block_height=items[cls.Index.LAST_GENERATE_BLOCK_HEIGHT],
                block_height=items[cls.Index.BLOCK_HEIGHT],
                tx_index=items[cls.Index.TX_INDEX],
                total_blocks=items[cls.Index.TOTAL_BLOCKS],
                validated_blocks=items[cls.Index.VALIDATED_BLOCKS],
                unvalidated_sequence_blocks=items[cls.Index.UNVALIDATED_SEQUENCE_BLOCKS]
            )
        else:
            raise InvalidParamsException("invalid version")

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
            grade=PRepGrade.CANDIDATE,

            # Optional items
            name=data.get(ConstantKeys.NAME, ""),
            country=data.get(ConstantKeys.COUNTRY, ""),
            city=data.get(ConstantKeys.CITY, ""),
            email=data.get(ConstantKeys.EMAIL, ""),
            website=data.get(ConstantKeys.WEBSITE, ""),
            details=data.get(ConstantKeys.DETAILS, ""),

            # Required items
            p2p_endpoint=data[ConstantKeys.P2P_ENDPOINT],
            irep=0,
            irep_block_height=block_height,

            # Registration time
            block_height=block_height,
            tx_index=tx_index
        )

    def to_dict(self, dict_type: 'PRepDictType') -> dict:
        """Returns the P-Rep information in dict format

        :param dict_type: FULL(getPRep), ABRIDGED(getPRepList)
        :return:
        """
        data = {
            "status": self._status.value,
            "penalty": self._penalty.value,
            "grade": self.grade.value,
            "name": self.name,
            "country": self.country,
            "city": self.city,
            "stake": self._stake,
            "delegated": self._delegated,
            "totalBlocks": self._total_blocks,
            "validatedBlocks": self._validated_blocks,
            "unvalidatedSequenceBlocks": self._unvalidated_sequence_blocks,
            "irep": self._irep,
            "irepUpdateBlockHeight": self._irep_block_height,
            "lastGenerateBlockHeight": self._last_generate_block_height,
        }

        if dict_type == PRepDictType.FULL:
            data[ConstantKeys.EMAIL] = self.email
            data[ConstantKeys.WEBSITE] = self.website
            data[ConstantKeys.DETAILS] = self.details
            data[ConstantKeys.P2P_ENDPOINT] = self.p2p_endpoint
            data[ConstantKeys.IREP] = self._irep
            data[ConstantKeys.IREP_BLOCK_HEIGHT] = self._irep_block_height
        else:
            data[ConstantKeys.ADDRESS] = self.address

        return data

    def __str__(self) -> str:
        return str(self.to_dict(PRepDictType.FULL))

    def copy(self, flags: 'PRepFlag' = PRepFlag.NONE) -> 'PRep':
        prep = copy.copy(self)
        prep._flags = flags

        return prep

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("P-Rep access denied")
