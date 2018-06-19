# Copyright 2017 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# The original codes exist in aio_pika.patterns.rpc

import asyncio
import time
from typing import Callable

from aio_pika.exchange import ExchangeType
from aio_pika.channel import Channel
from aio_pika.message import Message, IncomingMessage
from aio_pika.patterns.base import Base


class Server(Base):
    DLX_NAME = 'rpc.dlx'

    def __init__(self, channel: Channel, queue_name):
        self.channel = channel

        self.func_names = {}
        self.routes = {}

        self.queue_name = queue_name
        self.queue = None

        self.dlx_exchange = None

    @asyncio.coroutine
    def initialize_exchange(self):
        self.dlx_exchange = yield from self.channel.declare_exchange(
            self.DLX_NAME,
            type=ExchangeType.HEADERS,
            auto_delete=True,
        )

    @asyncio.coroutine
    def initialize_queue(self, **kwargs):
        arguments = kwargs.pop('arguments', {}).update({
            'x-dead-letter-exchange': self.DLX_NAME,
        })

        kwargs['arguments'] = arguments

        self.queue = yield from self.channel.declare_queue(name=self.queue_name, **kwargs)

    def create_callback(self, func_name, func):
        if func_name in self.routes:
            raise RuntimeError(
                'Method name already used for %r' % self.routes[func_name]
            )

        self.func_names[func] = func_name
        self.routes[func_name] = func

    @asyncio.coroutine
    def consume(self):
        yield from self.queue.consume(self.on_callback)

    @asyncio.coroutine
    def on_callback(self, message: IncomingMessage):
        func_name = message.headers['FuncName']
        if func_name not in self.routes:
            return

        payload = self.deserialize(message.body)
        func = self.routes[func_name]

        try:
            result = yield from self._execute(func, payload)
            result = self.serialize(result)
            message_type = 'result'
        except Exception as e:
            result = self.serialize(e)
            message_type = 'error'

        result_message = Message(
            result,
            delivery_mode=message.delivery_mode,
            correlation_id=message.correlation_id,
            timestamp=time.time(),
            type=message_type,
        )

        yield from self.channel.default_exchange.publish(
            result_message,
            message.reply_to,
            mandatory=False
        )

        message.ack()

    @asyncio.coroutine
    def _execute(self, func, payload):
        return (yield from func(**payload))


