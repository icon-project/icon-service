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

from .message import Request, Response


class MessageQueue(object):
    def __init__(self, loop):
        self._loop = loop
        self._requests = asyncio.Queue()
        self._msg_id_to_future = {}

    async def get(self) -> 'Request':
        return await self._requests.get()

    def put(self, request) -> asyncio.Future:
        assert isinstance(request, Request)

        future: asyncio.Future = self._loop.create_future()
        self._requests.put_nowait(request)
        self._msg_id_to_future[request.msg_id] = future

        return future

    def put_response(self, response: 'Response'):
        msg_id: int = response.msg_id

        future: asyncio.Future = self._msg_id_to_future[msg_id]
        del self._msg_id_to_future[msg_id]

        future.set_result(response)
