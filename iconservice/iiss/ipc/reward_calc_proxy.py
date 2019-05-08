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

__all__ = 'RewardCalcProxy'

import asyncio
import concurrent.futures
from typing import Optional

from iconcommons.logger import Logger

from .message import *
from .message_queue import MessageQueue
from .server import IPCServer
from ...base.address import Address

_TAG = "RCP"


class RewardCalcProxy(object):
    """Communicates with Reward Calculator through UNIX Domain Socket

    """

    def __init__(self):
        Logger.debug(tag=_TAG, msg="__init__() start")

        self._loop = None
        self._message_queue = None
        self._ipc_server = IPCServer()
        self._message_queue: Optional['MessageQueue'] = None
        self._calculation_result: Optional[tuple] = None

        Logger.debug(tag=_TAG, msg="__init__() end")

    def open(self, path: str):
        Logger.debug(tag=_TAG, msg="open() start")

        self._loop = asyncio.get_event_loop()
        self._message_queue = MessageQueue(self._loop)
        self._ipc_server.open(self._loop, self._message_queue, path)

        Logger.debug(tag=_TAG, msg="open() end")

    def start(self):
        Logger.debug(tag=_TAG, msg="start() end")
        self._ipc_server.start()
        Logger.debug(tag=_TAG, msg="start() end")

    def stop(self):
        Logger.debug(tag=_TAG, msg="stop() start")
        self._ipc_server.stop()
        Logger.debug(tag=_TAG, msg="stop() end")

    def close(self):
        Logger.debug(tag=_TAG, msg="close() start")

        future = self._ipc_server.close()
        asyncio.wait_for(future, 5)

        self._message_queue = None
        self._loop = None

        Logger.debug(tag=_TAG, msg="close() end")

    def get_version(self):
        Logger.debug(tag=_TAG, msg="get_version() start")

        future: concurrent.futures.Future = \
            asyncio.run_coroutine_threadsafe(self._get_version(), self._loop)

        response: 'VersionResponse' = future.result()

        Logger.debug(tag=_TAG, msg=f"get_version() end: {response.version}")

        return response.version

    async def _get_version(self):
        Logger.debug(tag=_TAG, msg="_get_version() start")

        request = VersionRequest()

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_get_version() end")

        return future.result()

    def calculate(self, db_path: str, block_height: int):
        """Request RewardCalculator to calculate IScore for every account

        It is called on invoke thread

        :param db_path: the absolute path of iiss database
        :param block_height: The blockHeight when this request are sent to RewardCalculator
        """
        Logger.debug(tag=_TAG, msg="calculate() start")

        asyncio.run_coroutine_threadsafe(
            self._calculate(db_path, block_height), self._loop)

        Logger.debug(tag=_TAG, msg="calculate() end")

    async def _calculate(self, db_path: str, block_height: int):
        Logger.debug(tag=_TAG, msg="_calculate() start")

        request = CalculateRequest(db_path, block_height)

        future: asyncio.Future = self._message_queue.put(request)
        future.add_done_callback(self.on_calculate_done)

        self._calculation_result: list = future.result()

        Logger.debug(tag=_TAG, msg=f"_calculate() end: {self._calculation_result}")

    def on_calculate_done(self, future: asyncio.Future):
        Logger.debug(tag=_TAG, msg="on_calculate_done() start")

        response: 'CalculateResponse' = future.result()
        self._calculation_result = \
            response.success, response.block_height, response.state_hash

        Logger.debug(tag=_TAG, msg="on_calculate_done() end")

    def claim_iscore(self, address: 'Address',
                     block_height: int, block_hash: bytes) -> int:
        """Claim IScore of a given address

        It is called on invoke thread

        :param address: the address to claim
        :param block_height: the height of block which contains this claim tx
        :param block_hash: the hash of block which contains this claim tx
        :return: [i-score(int), block_height(int)]
        """
        Logger.debug(
            tag=_TAG,
            msg=f"claim_iscore() start: address({address}) block_height({block_height}) block_hash({block_hash.hex()})"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._claim_iscore(address, block_height, block_hash), self._loop)

        response: 'ClaimResponse' = future.result()

        Logger.debug(tag=_TAG, msg=f"claim_iscore() end: iscore({response.iscore})")
        print(f"claim_iscore() end: iscore({response.iscore})")

        return response.iscore, response.block_height

    async def _claim_iscore(self, address: 'Address',
                            block_height: int, block_hash: bytes) -> int:
        Logger.debug(
            tag=_TAG,
            msg=f"_claim_iscore() start: address({address}) block_height({block_height}) block_hash({block_hash.hex()})"
        )
        request = ClaimRequest(address, block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg=f"_claim_iscore() end")

        return future.result()

    def query_iscore(self, address: 'Address') -> tuple:
        """Returns the I-Score of a given address

        It should be called on query thread

        :param address:
        :return: [i-score(int), block_height(int)]
        """
        Logger.debug(tag=_TAG, msg="query_iscore() start")

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._query_iscore(address), self._loop)

        response: 'QueryResponse' = future.result()

        Logger.debug(tag=_TAG, msg="query_iscore() end")

        return response.iscore, response.block_height

    async def _query_iscore(self, address: 'Address') -> list:
        """

        :param address:
        :return: [iscore(int), block_height(int)]
        """
        Logger.debug(tag=_TAG, msg="_query_iscore() start")

        request = QueryRequest(address)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_query_iscore() end")

        return future.result()

    def commit_block(self, success: bool, block_height: int, block_hash: bytes) -> tuple:
        """Notify reward calculator of block confirmation

        It is called on invoke thread

        :param success:
        :param block_height:
        :param block_hash:
        :return:
        """
        Logger.debug(
            tag=_TAG,
            msg=f"commit_block() start: success({success} block_height({block_height} block_hash({block_hash}"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._commit_block(success, block_height, block_hash), self._loop)

        response: 'CommitBlockResponse' = future.result()

        Logger.debug(tag=_TAG, msg="commit_block() end")

        return response.success, response.block_height, response.block_hash

    async def _commit_block(self, success: bool, block_height: int, block_hash: bytes) -> list:
        Logger.debug(tag=_TAG, msg="_commit_block() start")

        request = CommitBlockRequest(success, block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_commit_block() end")

        return future.result()
