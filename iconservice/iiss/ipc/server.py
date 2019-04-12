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


class IPCServer(object):
    def __init__(self):
        self._loop = None
        self._server = None

    def open(self, loop, on_accepted, path: str):
        assert loop
        assert on_accepted
        assert isinstance(path, str)

        self._loop = loop

        server = asyncio.start_unix_server(on_accepted, path)
        print(f"server_object: {server}")

        self._server = server

    def start(self):
        if self._server is not None:
            asyncio.ensure_future(self._server)

    def stop(self):
        if self._server is not None:
            self._server.close()

    async def close(self):
        if self._server is not None:
            await self._server.wait_closed()
            self._server = None

        self._loop = None
