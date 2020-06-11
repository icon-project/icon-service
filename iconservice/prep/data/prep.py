# -*- coding: utf-8 -*-
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
from enum import auto, IntEnum, Enum
from typing import TYPE_CHECKING, Tuple, Any, Optional

import iso3166

from .sorted_list import Sortable
from ...base.exception import AccessDeniedException
from ...base.type_converter_templates import ConstantKeys
from ...icon_constant import PRepGrade, PRepStatus, PenaltyReason, Revision, PRepFlag
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from iconservice.base.address import Address


class PRepDictType(Enum):
    FULL = auto()  # getPRep
    ABRIDGED = auto()  # getPReps


class PRep(Sortable):
    PREFIX: bytes = b"prep"
    _VERSION: int = 2
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

        NODE_ADDRESS = auto()

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
            unvalidated_sequence_blocks: int = 0,
            node_address: Optional['Address'] = None,

    ):
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
        :param node_address
        """
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
        self._name: str = name
        self._country: 'iso3166.Country' = self._get_country(country)
        self._city: str = city
        self._email: str = email
        self._website: str = website
        self._details: str = details
        # information required for PRep Consensus
        self._p2p_endpoint: str = p2p_endpoint
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

        self._is_frozen: bool = False

        # node key
        self._node_address = node_address if node_address else address

    def is_flags_on(self, flags: 'PRepFlag') -> bool:
        return (self._flags & flags) == flags

    def is_dirty(self) -> bool:
        """It returns True if any PRepFlag is True

        :return:
        """
        return bool(self._flags & PRepFlag.ALL)

    @property
    def flags(self) -> 'PRepFlag':
        return self._flags

    @property
    def status(self) -> 'PRepStatus':
        return self._status

    @status.setter
    def status(self, value: 'PRepStatus'):
        self._set_property(name="_status", new_value=value, flags=PRepFlag.STATUS)

    @property
    def penalty(self) -> 'PenaltyReason':
        return self._penalty

    @penalty.setter
    def penalty(self, value: 'PenaltyReason'):
        self._set_property(name="_penalty", new_value=value, flags=PRepFlag.PENALTY)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._set_property(name="_name", new_value=value, flags=PRepFlag.NAME)

    @property
    def country(self) -> str:
        return self._country.alpha3

    @country.setter
    def country(self, alpha3_country_code: str):
        value = self._get_country(alpha3_country_code)
        self._set_property(name="_country", new_value=value, flags=PRepFlag.COUNTRY)

    @classmethod
    def _get_country(cls, alpha3_country_code: str) -> 'iso3166.Country':
        return iso3166.countries_by_alpha3.get(
            alpha3_country_code.upper(), cls._UNKNOWN_COUNTRY)

    @property
    def city(self) -> str:
        return self._city

    @city.setter
    def city(self, value: str):
        self._set_property(name="_city", new_value=value, flags=PRepFlag.CITY)

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        self._set_property(name="_email", new_value=value, flags=PRepFlag.EMAIL)

    @property
    def website(self) -> str:
        return self._website

    @website.setter
    def website(self, value: str):
        self._set_property(name="_website", new_value=value, flags=PRepFlag.WEBSITE)

    @property
    def details(self) -> str:
        return self._details

    @details.setter
    def details(self, value: str):
        self._set_property(name="_details", new_value=value, flags=PRepFlag.DETAILS)

    @property
    def p2p_endpoint(self) -> str:
        return self._p2p_endpoint

    @p2p_endpoint.setter
    def p2p_endpoint(self, value: str):
        self._set_property(name="_p2p_endpoint", new_value=value, flags=PRepFlag.P2P_ENDPOINT)

    def is_suspended(self) -> bool:
        """The suspended P-Rep cannot serve as Main P-Rep during this term

        :return:
        """
        return self._penalty == PenaltyReason.BLOCK_VALIDATION

    def is_electable(self) -> bool:
        """Returns whether this P-Rep can be elected as a Main P-Rep or Sub P-Rep

        :return:
        """
        return self._status == PRepStatus.ACTIVE and self._penalty == PenaltyReason.NONE

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
        self._set_property(name="_grade", new_value=value, flags=PRepFlag.GRADE)

    def update_block_statistics(self, is_validator: bool):
        """Update the block validation statistics of P-Rep

        :param is_validator: If this P-Rep validates a block, then it is True
        """
        self._check_access_permission()

        self._set_property("_total_blocks", self._total_blocks + 1, PRepFlag.TOTAL_BLOCKS, False)

        if is_validator:
            self._set_property("_validated_blocks", self._validated_blocks + 1, PRepFlag.VALIDATED_BLOCKS, False)
            self._set_property("_unvalidated_sequence_blocks", 0, PRepFlag.UNVALIDATED_SEQUENCE_BLOCKS, False)
        else:
            self._set_property(
                "_unvalidated_sequence_blocks",
                self._unvalidated_sequence_blocks + 1,
                PRepFlag.UNVALIDATED_SEQUENCE_BLOCKS,
                False)

    def reset_block_validation_penalty(self):
        """Reset block validation penalty and
        unvalidated sequence blocks before the next term begins

        :return:
        """
        self._check_access_permission()
        self._set_property("_penalty", PenaltyReason.NONE, PRepFlag.PENALTY, False)
        self._set_property("_unvalidated_sequence_blocks", 0, PRepFlag.UNVALIDATED_SEQUENCE_BLOCKS, False)

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
    def node_address(self) -> 'Address':
        return self._node_address

    @node_address.setter
    def node_address(self, value: 'Address'):
        self._set_property(name="_node_address", new_value=value, flags=PRepFlag.NODE_ADDRESS)

    @property
    def stake(self) -> int:
        return self._stake

    @stake.setter
    def stake(self, value: int):
        """stake is set to account.stake

        :param value:
        :return:
        """
        assert value >= 0
        self._set_property(name="_stake", new_value=value, flags=PRepFlag.STAKE)

    @property
    def delegated(self) -> int:
        return self._delegated

    @delegated.setter
    def delegated(self, value: int):
        """delegated is set to account.delegated_amount

        :param value:
        :return:
        """
        assert value >= 0
        self._set_property(name="_delegated", new_value=value, flags=PRepFlag.DELEGATED)

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
        self._set_property(name="_last_generate_block_height",
                           new_value=value,
                           flags=PRepFlag.LAST_GENERATE_BLOCK_HEIGHT)

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
        return self._is_frozen

    def freeze(self):
        """Make all member variables immutable
        """
        self._is_frozen = True
        self._flags = PRepFlag.NONE

    def set(self,
            *,
            name: str = None,
            country: str = None,
            city: str = None,
            email: str = None,
            website: str = None,
            details: str = None,
            p2p_endpoint: str = None,
            node_address: 'Address' = None):
        """Update PRep properties on processing setPRep JSON-RPC API
        Not allowed to update some properties which can affect PRep order or are immutable

        :param name:
        :param country: alpha3 country code
        :param city:
        :param email:
        :param website:
        :param details:
        :param p2p_endpoint:
        :param node_address:
        """
        self._check_access_permission()

        kwargs = {
            "name": name,
            "country": country,
            "city": city,
            "email": email,
            "website": website,
            "details": details,
            "p2p_endpoint": p2p_endpoint,
            "node_address": node_address
        }

        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)

    def set_irep(self, irep: int, block_height: int):
        """Set incentive rep

        :param irep:
        :param block_height: block height when irep is set
        :return:
        """
        self._check_access_permission()

        self._set_property("_irep", irep, PRepFlag.IREP, False)
        self._set_property("_irep_block_height", block_height, PRepFlag.IREP_BLOCK_HEIGHT, False)

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
        if revision >= Revision.DIVIDE_NODE_ADDRESS.value:
            version: int = 2
        elif revision >= Revision.DECENTRALIZATION.value:
            version: int = 1
        else:
            version: int = 0

        data = [
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
            self._validated_blocks,
        ]

        if version >= 1:
            data.extend((self.penalty.value, self._unvalidated_sequence_blocks))

        if version >= 2:
            data.append(self._node_address)

        return MsgPackForDB.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PRep':
        items: list = MsgPackForDB.loads(data)
        version: int = items[cls.Index.VERSION]

        if version == 0:
            items.extend((PenaltyReason.NONE, 0))

        if version < 2:
            items.append(items[cls.Index.ADDRESS])

        return PRep(
            # version 0
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
            validated_blocks=items[cls.Index.VALIDATED_BLOCKS],

            # version 1
            penalty=PenaltyReason(items[cls.Index.PENALTY]),
            unvalidated_sequence_blocks=items[cls.Index.UNVALIDATED_SEQUENCE_BLOCKS],

            # version 2
            node_address=items[cls.Index.NODE_ADDRESS],
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
            tx_index=tx_index,

            # node key
            node_address=data.get(ConstantKeys.NODE_ADDRESS)
        )

    def to_dict(self, dict_type: 'PRepDictType') -> dict:
        """Returns the P-Rep information in dict format

        :param dict_type: FULL(getPRep), ABRIDGED(getPReps)
        :return:
        """
        data = {
            "address": self._address,
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
            "blockHeight": self._block_height,
            "txIndex": self._tx_index,
            "nodeAddress": self._node_address,
        }
        # TODO Revision: remove irep, irepUpdateBlockHeight after SET_IREP_VIA_NETWORK_PROPOSAL

        if dict_type == PRepDictType.FULL:
            data[ConstantKeys.EMAIL] = self.email
            data[ConstantKeys.WEBSITE] = self.website
            data[ConstantKeys.DETAILS] = self.details
            data[ConstantKeys.P2P_ENDPOINT] = self.p2p_endpoint

        return data

    def __str__(self) -> str:
        info: dict = self.to_dict(PRepDictType.FULL)
        return str(info)

    def copy(self) -> 'PRep':
        prep = copy.copy(self)
        prep._is_frozen = False
        prep._flags = PRepFlag.NONE

        return prep

    def _check_access_permission(self):
        if self.is_frozen():
            raise AccessDeniedException("P-Rep access denied")

    def _set_property(self, name: str, new_value: Any, flags: 'PRepFlag', check_permission: bool = True):
        if check_permission:
            self._check_access_permission()

        old_value = getattr(self, name)
        if old_value != new_value:
            setattr(self, name, new_value)
            self._flags |= flags
