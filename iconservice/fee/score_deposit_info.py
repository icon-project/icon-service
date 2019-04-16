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


class ScoreDepositInfo(object):
    """
    SScoreDepositInfo Class implementing functions to serialize and deserialize.
    """

    def __init__(self, head_id: bytes = None, tail_id: bytes = None,
                 available_head_id_of_virtual_step: bytes = None, available_head_id_of_deposit: bytes = None,
                 expires_of_virtual_step: int = -1, expires_of_deposit: int = -1, version: int = 0):
        self.head_id = head_id
        self.tail_id = tail_id
        self.available_head_id_of_virtual_step = available_head_id_of_virtual_step
        self.available_head_id_of_deposit = available_head_id_of_deposit
        self.expires_of_virtual_step = expires_of_virtual_step
        self.expires_of_deposit = expires_of_deposit
        self.version = version

    @staticmethod
    def from_bytes(buf: bytes):
        """Converts ScoreDepositInfo in bytes into ScoreDepositInfo Object.

        :param buf: ScoreDepositInfo in bytes
        :return: ScoreDepositInfo Object
        """
        data: list = MsgPackForDB.loads(buf)

        score_deposit_info = ScoreDepositInfo()
        score_deposit_info.head_id = data[0]
        score_deposit_info.tail_id = data[1]
        score_deposit_info.available_head_id_of_virtual_step = data[2]
        score_deposit_info.available_head_id_of_deposit = data[3]
        score_deposit_info.expires_of_virtual_step = data[4]
        score_deposit_info.expires_of_deposit = data[5]
        score_deposit_info.version = data[6]

        return score_deposit_info

    def to_bytes(self) -> bytes:
        """Converts ScoreDepositInfo object into bytes.

        :return: ScoreDepositInfo in bytes
        """
        data: list = [self.head_id, self.tail_id,
                      self.available_head_id_of_virtual_step, self.available_head_id_of_deposit,
                      self.expires_of_virtual_step, self.expires_of_deposit, self.version]
        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Fee)
        """
        return isinstance(other, ScoreDepositInfo) \
               and self.head_id == other.head_id \
               and self.tail_id == other.tail_id \
               and self.available_head_id_of_virtual_step == other.available_head_id_of_virtual_step \
               and self.available_head_id_of_deposit == other.available_head_id_of_deposit \
               and self.expires_of_virtual_step == other.expires_of_virtual_step \
               and self.expires_of_deposit == other.expires_of_deposit \
               and self.version == other.version

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Fee)
        """
        return not self.__eq__(other)
