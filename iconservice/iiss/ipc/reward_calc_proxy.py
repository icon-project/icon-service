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

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING, Optional

import msgpack

from .message import *
from .message_queue import MessageQueue
from .server import IPCServer
from ...base.address import Address

if TYPE_CHECKING:
    from asyncio.streams import StreamReader, StreamWriter


class RewardCalcProxy(object):
    """Communicates with Reward Calculator through UNIX Domain Socket

    """

    def __init__(self):
        self._msg_id = None
        self._loop = None
        self._queue = None
        self._msgs_to_recv = None
        self._server_task = None
        self._message_queue: Optional['MessageQueue'] = None
        self._ipc_server = IPCServer()
        self._calculation_result: Optional[list] = None
        self._unpacker = None

    def open(self, path: str):
        self._loop = asyncio.get_event_loop()
        self._queue = asyncio.Queue()
        self._msgs_to_recv = {}
        self._msg_id = 0

        self._unpacker = msgpack.Unpacker(raw=True)
        self._ipc_server.open(self._loop, self._on_accepted, path)

    def _on_accepted(self, reader: 'StreamReader', writer: 'StreamWriter'):
        print(f"on_accepted() start: {reader} {writer}")

        asyncio.ensure_future(self.on_send(writer))
        asyncio.ensure_future(self.on_recv(reader))

        print("on_accepted() end")

    async def on_send(self, writer: 'StreamWriter'):
        while True:
            item: list = await self._queue.get()
            print(item)

            payload: list = item[0]

            msg_id: int = payload[1]
            self._msgs_to_recv[msg_id] = item

            data: bytes = msgpack.packb(payload)
            print(f"on_send(): data({data.hex()}")

            writer.write(data)
            await writer.drain()

    async def on_recv(self, reader: 'StreamReader'):
        while True:
            data: bytes = await reader.read(1024)
            print(f"on_recv(): data({data.hex()})")

            self._unpacker.feed(data)

            for response in self._unpacker:
                if isinstance(response, list):
                    msg_id: int = response[1]
                    payload: list = response[2]

                    request: list = self._msgs_to_recv[msg_id]
                    future: asyncio.Future = request[1]
                    future.set_result(payload)

                    del self._msgs_to_recv[msg_id]
                else:
                    raise Exception

    def start(self):
        self._ipc_server.start()

    def stop(self):
        self._ipc_server.stop()

    def close(self):
        future = self._ipc_server.close()
        asyncio.wait_for(future, 5)

        self._loop = None

    def get_version(self):
        future: concurrent.futures.Future = \
            asyncio.run_coroutine_threadsafe(self._get_version(), self._loop)

        response: 'VersionResponse' = future.result()
        return response.version

    async def _get_version(self):
        request = VersionRequest()

        future: asyncio.Future = self._message_queue.put(request)
        await future

        return future.result()

    def calculate(self, db_path: str, block_height: int):
        """Request RewardCalculator to calculate IScore for every account

        :param db_path: the absolute path of iiss database
        :param block_height: The blockHeight when this request are sent to RewardCalculator
        """
        asyncio.run_coroutine_threadsafe(
            self._calculate(db_path, block_height), self._loop)

    async def _calculate(self, db_path: str, block_height: int):
        request = CalculateRequest(db_path, block_height)

        future: asyncio.Future = self._message_queue.put(request)
        future.add_done_callback(self.on_calculate_done)

        self._calculation_result: list = future.result()

    def on_calculate_done(self, future: asyncio.Future):
        print("on_calculate_done")
        response: 'CalculateResponse' = future.result()
        success: bool = response.success

    def claim_iscore(self, address: 'Address',
                     block_height: int, block_hash: bytes) -> int:
        """Claim IScore of a given address

        :param address: the address to claim
        :param block_height: the height of block which contains this claim tx
        :param block_hash: the hash of block which contains this claim tx
        :return: [i-score(int), block_height(int)]
        """
        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._claim_iscore(address, block_height, block_hash))

        response: 'ClaimResponse' = future.result()
        return response.iscore

    async def _claim_iscore(self, address: 'Address',
                            block_height: int, block_hash: bytes) -> int:
        request = ClaimRequest(address, block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        return future.result()

    def query_iscore(self, address: 'Address') -> tuple:
        """Returns the I-Score of a given address

        It should be called on not main thread but query thread.

        :param address:
        :return: [i-score(int), block_height(int)]
        """
        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._query_iscore(address), self._loop)

        response: 'QueryResponse' = future.result()
        return response.iscore, response.block_height

    async def _query_iscore(self, address: 'Address') -> list:
        """

        :param address:
        :return: [iscore(int), block_height(int)]
        """
        request = QueryRequest(address)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        return future.result()

    def commit_block(self, success: bool, block_height: int, block_hash: bytes) -> tuple:
        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._commit_block(success, block_height, block_hash), self._loop)

        response: 'CommitBlockResponse' = future.result()
        return response.success, response.block_height, response.block_hash

    async def _commit_block(self, success: bool, block_height: int, block_hash: bytes) -> list:
        request = CommitBlockRequest(success, block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        return future.result()
