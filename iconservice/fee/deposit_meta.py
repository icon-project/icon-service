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

from ..utils.msgpack_for_db import MsgPackForDB


class DepositMeta(object):
    """
    DepositMeta Class implementing functions to serialize and deserialize.
    """
    _VERSION = 0

    def __init__(self, head_id: bytes = None, tail_id: bytes = None,
                 available_head_id_of_virtual_step: bytes = None, available_head_id_of_deposit: bytes = None,
                 expires_of_virtual_step: int = -1, expires_of_deposit: int = -1):
        self.version = self._VERSION
        self.head_id = head_id
        self.tail_id = tail_id
        self.available_head_id_of_virtual_step = available_head_id_of_virtual_step
        self.available_head_id_of_deposit = available_head_id_of_deposit
        self.expires_of_virtual_step = expires_of_virtual_step
        self.expires_of_deposit = expires_of_deposit

    @staticmethod
    def from_bytes(buf: bytes):
        """Converts DepositMeta in bytes into DepositMeta Object.

        :param buf: DepositMeta in bytes
        :return: DepositMeta Object
        """
        data: list = MsgPackForDB.loads(buf)

        deposit_meta = DepositMeta()
        deposit_meta.version = data[0]
        deposit_meta.head_id = data[1]
        deposit_meta.tail_id = data[2]
        deposit_meta.available_head_id_of_virtual_step = data[3]
        deposit_meta.available_head_id_of_deposit = data[4]
        deposit_meta.expires_of_virtual_step = data[5]
        deposit_meta.expires_of_deposit = data[6]

        return deposit_meta

    def to_bytes(self) -> bytes:
        """Converts DepositMeta object into bytes.

        :return: DepositMeta in bytes
        """
        data: list = [self.version, self.head_id, self.tail_id,
                      self.available_head_id_of_virtual_step, self.available_head_id_of_deposit,
                      self.expires_of_virtual_step, self.expires_of_deposit]
        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (DepositMeta)
        """
        return isinstance(other, DepositMeta) \
            and self.version == other.version \
            and self.head_id == other.head_id \
            and self.tail_id == other.tail_id \
            and self.available_head_id_of_virtual_step == other.available_head_id_of_virtual_step \
            and self.available_head_id_of_deposit == other.available_head_id_of_deposit \
            and self.expires_of_virtual_step == other.expires_of_virtual_step \
            and self.expires_of_deposit == other.expires_of_deposit

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (DepositMeta)
        """
        return not self.__eq__(other)
