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
from typing import Callable, Any, Optional, Dict

from iconcommons.logger import Logger
from iconservice.base.exception import InvalidParamsException, ServiceNotReadyException
from iconservice.icon_constant import RCStatus
from .message import Request, Response, MessageType


class MessageQueue(object):
    def __init__(self, loop, notify_message: tuple = None, notify_handler: Callable[['Response'], Any] = None):
        if notify_handler is None and notify_message is not None:
            raise InvalidParamsException("Failed to construct MessageQueue instance."
                                         "If notify_message is not None, notify_handler is mandatory parameter")
        self._loop = loop
        self._requests = asyncio.Queue()
        self._msg_id_to_future: Dict[int, asyncio.Future] = {}
        self.notify_message: Optional[tuple] = notify_message
        self.notify_handler = notify_handler
        self._rc_status = RCStatus.NOT_READY

    async def get(self) -> 'Request':
        return await self._requests.get()

    def put(self, request, wait_for_response: bool = True) -> Optional[asyncio.Future]:
        assert isinstance(request, Request)

        self._requests.put_nowait(request)

        if wait_for_response:
            future: asyncio.Future = self._loop.create_future()
            self._msg_id_to_future[request.msg_id] = future
            return future

    def task_done(self):
        self._requests.task_done()

    def message_handler(self, response: 'Response'):
        msg_type: MessageType = getattr(response, "MSG_TYPE")

        if self._rc_status == RCStatus.NOT_READY:
            if msg_type == MessageType.READY:
                self._rc_status = RCStatus.READY
            else:
                raise ServiceNotReadyException(f"Ready notification did not arrive: {response}")

        if response.is_notification():
            self.notify_handler(response)
            return

        try:
            self.put_response(response)
        except KeyError:
            Logger.warning(f"Unexpected response arrived.  Respond Id : {response.msg_id}")

    def put_response(self, response: 'Response'):
        msg_id: int = response.msg_id

        future: asyncio.Future = self._msg_id_to_future[msg_id]

        del self._msg_id_to_future[msg_id]

        future.set_result(response)
