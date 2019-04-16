# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional

from ..base.address import Address
from ..utils.msgpack_for_db import MsgPackForDB


class Deposit(object):
    """
    Deposit Information Class
    implementing functions to serialize, deserialize and convert to dict type.
    """

    def __init__(self, deposit_id: bytes = None, score_address: 'Address' = None, sender: 'Address' = None,
                 deposit_amount: int = 0, deposit_used: int = 0, created: int = 0, expires: int = -1,
                 virtual_step_issued: int = 0, virtual_step_used: int = 0, prev_id: bytes = None,
                 next_id: bytes = None, version: int = 0):
        # deposit id, should be tx hash of deposit transaction
        self.id = deposit_id
        # target SCORE address
        self.score_address = score_address
        # sender address
        self.sender = sender
        # deposit amount of ICXs in loop
        self.deposit_amount = deposit_amount
        # used amount of deposited ICXs in loop
        self.deposit_used = deposit_used
        # created time in block
        self.created = created
        # expires time in block
        self.expires = expires
        # issued amount of virtual STEPs
        self.virtual_step_issued = virtual_step_issued
        # used amount of virtual STEPs
        self.virtual_step_used = virtual_step_used
        # previous id of this deposit
        self.prev_id = prev_id
        # next id of this deposit
        self.next_id = next_id
        self.version = version

    @staticmethod
    def from_bytes(buf: bytes):
        """Creates Deposit object from bytes data.

        :param buf: deposit info in bytes
        :return: deposit object
        """
        data: list = MsgPackForDB.loads(buf)

        deposit = Deposit()
        deposit.score_address = data[0]
        deposit.sender = data[1]
        deposit.deposit_amount = data[2]
        deposit.deposit_used = data[3]
        deposit.created = data[4]
        deposit.expires = data[5]
        deposit.virtual_step_issued = data[6]
        deposit.virtual_step_used = data[7]
        deposit.prev_id = data[8]
        deposit.next_id = data[9]
        deposit.version = data[10]

        return deposit

    def to_bytes(self) -> bytes:
        """Converts Deposit object into bytes.

        :return: deposit info in bytes
        """
        data: list = [self.score_address,
                      self.sender,
                      self.deposit_amount,
                      self.deposit_used,
                      self.created,
                      self.expires,
                      self.virtual_step_issued,
                      self.virtual_step_used,
                      self.prev_id,
                      self.next_id,
                      self.version]

        return MsgPackForDB.dumps(data)

    def to_dict(self, casing: Optional = None) -> dict:
        """Returns properties as dict.

        :param casing: a kind of functions to convert one casing notation to another
        :return: deposit info in dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            # Excludes properties which have `None` value
            if value is None:
                continue

            new_key = casing(key) if casing else key
            new_dict[new_key] = value

        return new_dict

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Deposit)
        """
        return isinstance(other, Deposit) \
               and self.score_address == other.score_address \
               and self.sender == other.sender \
               and self.deposit_amount == other.deposit_amount \
               and self.deposit_used == other.deposit_used \
               and self.created == other.created \
               and self.expires == other.expires \
               and self.virtual_step_issued == other.virtual_step_issued \
               and self.virtual_step_used == other.virtual_step_used \
               and self.prev_id == other.prev_id \
               and self.next_id == other.next_id \
               and self.version == other.version

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Deposit)
        """
        return not self.__eq__(other)

    @property
    def remaining_virtual_step(self):
        """
        the amount of available virtual step
        """
        return self.virtual_step_issued - self.virtual_step_used

    @property
    def remaining_deposit(self):
        """
        the amount of available deposit for fees
        """
        return self.deposit_amount - self.deposit_used
