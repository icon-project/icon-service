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
from asyncio import StreamReader, StreamWriter
from typing import Optional

from iconcommons import Logger

from .message import MessageType, Request, NoneRequest, NoneResponse, VersionResponse
from .message_queue import MessageQueue
from .message_unpacker import MessageUnpacker


class IPCServer(object):
    def __init__(self):
        self._loop = None
        self._server = None
        self._queue: Optional['MessageQueue'] = None
        self._unpacker: Optional['MessageUnpacker'] = MessageUnpacker()

    def open(self, loop,  message_queue: 'MessageQueue', path: str):
        assert loop
        assert message_queue
        assert isinstance(path, str)

        self._loop = loop
        self._queue = message_queue

        server = asyncio.start_unix_server(self._on_accepted, path)
        print(f"server_object: {server}")

        self._server = server

    def start(self):
        if self._server is None:
            return

        asyncio.ensure_future(self._server)

    def stop(self):
        if self._server is None:
            return

        self._server.close()

    async def close(self):
        if self._server is not None:
            await self._server.wait_closed()
            self._server = None

        self._loop = None
        self._queue = None
        self._unpacker = None

    def _on_accepted(self, reader: 'StreamReader', writer: 'StreamWriter'):
        print(f"on_accepted() start: {reader} {writer}")

        asyncio.ensure_future(self._on_send(writer))
        asyncio.ensure_future(self._on_recv(reader))

        print("on_accepted() end")

    async def _on_send(self, writer: 'StreamWriter'):
        print("_on_send() start")

        while True:
            request: 'Request' = await self._queue.get()
            if request.msg_type == MessageType.NONE:
                self._queue.put_response(
                    NoneResponse.from_list([request.msg_type, request.msg_id])
                )
                break

            print(request)

            data: bytes = request.to_bytes()
            print(f"on_send(): data({data.hex()}")

            writer.write(data)
            await writer.drain()

        writer.close()

        print("_on_send() end")

    async def _on_recv(self, reader: 'StreamReader'):
        print("_on_recv() start")

        while True:
            data: bytes = await reader.read(1024)
            if not isinstance(data, bytes) or len(data) == 0:
                break

            print(f"on_recv(): data({data.hex()})")

            self._unpacker.feed(data)

            for response in self._unpacker:
                if not isinstance(response, VersionResponse):
                    self._queue.put_response(response)
                else:
                    Logger.debug(f"{response.version}", "RCP")

        await self._queue.put(NoneRequest())

        print("_on_recv() end")