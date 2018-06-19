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
import logging
import time

from concurrent import futures
from aio_pika.exchange import ExchangeType
from aio_pika.channel import Channel
from aio_pika.exceptions import UnroutableError
from aio_pika.message import Message, IncomingMessage, DeliveryMode, ReturnedMessage
from aio_pika.tools import create_future
from aio_pika.patterns.base import Base


class ClientAsync(Base):
    DLX_NAME = 'rpc.dlx'

    def __init__(self, channel: Channel, queue_name):
        self.channel = channel
        self.queue_name = queue_name
        self.queue = None
        self.result_queue = None

        self.async_futures = {}
        self.concurrent_futures = {}

        self.func_names = {}
        self.routes = {}

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

        self.result_queue = yield from self.channel.declare_queue(None, exclusive=True, auto_delete=True)
        yield from self.result_queue.bind(
            self.dlx_exchange, "",
            arguments={
                "From": self.result_queue.name,
                'x-match': 'any',
            }
        )

        yield from self.result_queue.consume(
            self._on_result_message, no_ack=True
        )

        self.channel.add_on_return_callback(self._on_message_returned)

    def _on_message_returned(self, message: ReturnedMessage):
        correlation_id = int(message.correlation_id) if message.correlation_id else None

        future = self.async_futures.pop(correlation_id, None) or self.concurrent_futures.pop(correlation_id, None)
        if future and future.done():
            logging.warning("Unknown message was returned: %r", message)
        else:
            future.set_exception(UnroutableError([message]))

    @asyncio.coroutine
    def _on_result_message(self, message: IncomingMessage):
        correlation_id = int(message.correlation_id) if message.correlation_id else None
        try:
            future = self.async_futures[correlation_id]  # type: asyncio.Future
        except KeyError:
            pass
        else:
            payload = self.deserialize(message.body)

            if message.type == 'result':
                future.set_result(payload)
            elif message.type == 'error':
                future.set_exception(payload)
            elif message.type == 'call':
                future.set_exception(asyncio.TimeoutError("Message timed-out", message))
            else:
                future.set_exception(RuntimeError("Unknown message type %r" % message.type))

    @asyncio.coroutine
    def call(self, func_name, kwargs: dict=None, *, expiration: int=None,
             priority: int=128, delivery_mode: DeliveryMode=DeliveryMode.NOT_PERSISTENT):
        future = self._create_future()
        message = Message(
            body=self.serialize(kwargs or {}),
            type='call',
            timestamp=time.time(),
            expiration=expiration,
            priority=priority,
            correlation_id=id(future),
            delivery_mode=delivery_mode,
            reply_to=self.result_queue.name,
            headers={
                'From': self.result_queue.name,
                'FuncName': func_name
            },
        )

        yield from self.channel.default_exchange.publish(
            message, routing_key=self.queue_name, mandatory=True
        )

        return (yield from future)

    def _create_future(self) -> asyncio.Future:
        future = create_future(loop=self.channel.loop)
        future_id = id(future)
        self.async_futures[future_id] = future
        future.add_done_callback(lambda f: self.async_futures.pop(future_id, None))
        return future
