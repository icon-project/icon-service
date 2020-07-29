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
from .message import MessageType, Request
from .message_queue import MessageQueue
from .message_unpacker import MessageUnpacker

_TAG = "RCP"


class IPCServer(object):
    def __init__(self):
        self._running = False
        self._loop = None
        self._path = None
        self._queue: Optional['MessageQueue'] = None
        self._unpacker: Optional['MessageUnpacker'] = MessageUnpacker()
        self._tasks = []

    def open(self, loop,  message_queue: 'MessageQueue', path: str):
        Logger.info(tag=_TAG, msg="open() start")

        assert loop
        assert message_queue
        assert isinstance(path, str)

        self._loop = loop
        self._queue = message_queue
        self._path = path

        Logger.info(tag=_TAG, msg="open() end")

    def start(self):
        Logger.info(tag=_TAG, msg="start() start")

        if self._running:
            return

        self._running = True
        co = asyncio.start_unix_server(self._on_accepted, self._path)
        asyncio.ensure_future(co)

        Logger.info(tag=_TAG, msg="start() end")

    def stop(self):
        Logger.info(tag=_TAG, msg="stop() start")

        if not self._running:
            return

        self._running = False

        for t in self._tasks:
            t.cancel()

        Logger.info(tag=_TAG, msg="stop() end")

    def close(self):
        Logger.info(tag=_TAG, msg="close() start")

        self._loop = None
        self._unpacker = None

        Logger.info(tag=_TAG, msg="close() end")

    def _on_accepted(self, reader: 'StreamReader', writer: 'StreamWriter'):
        Logger.info(tag=_TAG, msg=f"on_accepted() start: {reader} {writer}")

        self._tasks.append(asyncio.ensure_future(self._on_send(writer)))
        self._tasks.append(asyncio.ensure_future(self._on_recv(reader)))

        Logger.info(tag=_TAG, msg="on_accepted() end")

    async def _on_send(self, writer: 'StreamWriter'):
        Logger.info(tag=_TAG, msg="_on_send() start")

        while self._running:
            try:
                request: 'Request' = await self._queue.get()
                self._queue.task_done()

                if request.msg_type == MessageType.NONE:
                    # Stopping IPCServer
                    break

                data: bytes = request.to_bytes()
                Logger.debug(tag=_TAG, msg=f"on_send(): data({data.hex()}")
                Logger.info(tag=_TAG, msg=f"Sending Data : {request}")
                writer.write(data)
                await writer.drain()

            except asyncio.CancelledError:
                # task got cancel request. stop service
                break
            except BaseException as e:
                Logger.warning(tag=_TAG, msg=str(e))

        writer.close()

        Logger.info(tag=_TAG, msg="_on_send() end")

    async def _on_recv(self, reader: 'StreamReader'):
        Logger.info(tag=_TAG, msg="_on_recv() start")

        while self._running:
            try:
                data: bytes = await reader.read(1024)
                if not isinstance(data, bytes) or len(data) == 0:
                    break

                Logger.debug(tag=_TAG, msg=f"_on_recv(): data({data.hex()})")

                self._unpacker.feed(data)

                for response in self._unpacker:
                    Logger.info(tag=_TAG, msg=f"Received Data : {response}")
                    self._queue.message_handler(response)

            except asyncio.CancelledError:
                # task got cancel request. stop service
                break
            except BaseException as e:
                Logger.warning(tag=_TAG, msg=str(e))

        Logger.info(tag=_TAG, msg="_on_recv() end")
