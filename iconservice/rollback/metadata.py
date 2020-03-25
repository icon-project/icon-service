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

__all__ = "Metadata"

from typing import Optional

from iconcommons.logger import Logger
from ..base.block import Block
from ..icon_constant import ROLLBACK_LOG_TAG
from ..icon_constant import Revision
from ..utils import bytes_to_hex
from ..utils.msgpack_for_db import MsgPackForDB

TAG = ROLLBACK_LOG_TAG


class Metadata(object):
    """Contains rollback metadata

    """
    _VERSION = 0

    def __init__(self, block_height: int, block_hash: bytes, term_start_block_height: int, last_block: 'Block'):
        """

        :param block_height: final block_height after rollback
        :param block_hash: final block_hash after rollback
        :param term_start_block_height: the start block height of the current term
        :param last_block: the last block before rollback
        """
        self._block_height = block_height
        self._block_hash = block_hash
        self._last_block = last_block
        self._term_start_block_height = term_start_block_height

    @property
    def block_height(self) -> int:
        return self._block_height

    @property
    def block_hash(self) -> bytes:
        return self._block_hash

    @property
    def last_block(self) -> 'Block':
        return self._last_block

    @property
    def term_start_block_height(self) -> int:
        return self._term_start_block_height

    def __eq__(self, other):
        return self._block_height == other.block_height \
               and self._block_hash == other.block_hash \
               and self._term_start_block_height == other.term_start_block_height \
               and self._last_block == other.last_block

    def __str__(self):
        return f"rollback.Metadata(" \
               f"block_height={self._block_height} " \
               f"block_hash={bytes_to_hex(self._block_hash)} " \
               f"term_start_block_height={self._term_start_block_height} " \
               f"last_block={self._last_block})"

    @classmethod
    def from_bytes(cls, buf: bytes) -> 'Metadata':
        data: list = MsgPackForDB.loads(buf)
        version: int = data[0]
        assert version == cls._VERSION

        block_height: int = data[1]
        block_hash: bytes = data[2]
        term_start_block_height: int = data[3]
        last_block: 'Block' = Block.from_bytes(data[4])

        return Metadata(block_height, block_hash, term_start_block_height, last_block)

    def to_bytes(self) -> bytes:
        data = [
            self._VERSION,
            self._block_height,
            self._block_hash,
            self._term_start_block_height,
            self._last_block.to_bytes(Revision.IISS.value)
        ]

        return MsgPackForDB.dumps(data)

    @classmethod
    def load(cls, path: str) -> Optional['Metadata']:
        Logger.debug(tag=TAG, msg=f"load() start: {path}")

        metadata = None

        try:
            with open(path, "rb") as f:
                buf: bytes = f.read()
                metadata = Metadata.from_bytes(buf)
        except FileNotFoundError:
            Logger.debug(tag=TAG, msg=f"File not found: {path}")
        except BaseException as e:
            Logger.info(tag=TAG, msg=f"Unexpected error: {str(e)}")

        Logger.debug(tag=TAG, msg=f"load() end: metadata={metadata}")
        return metadata

    def save(self, path: str):
        Logger.debug(tag=TAG, msg=f"save() start: {path}")

        with open(path, "wb") as f:
            f.write(self.to_bytes())

        Logger.debug(tag=TAG, msg=f"save() end")
