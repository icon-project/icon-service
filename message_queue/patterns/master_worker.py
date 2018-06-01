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

# The original codes exist in aio_pika.patterns.master

import asyncio
import logging

from typing import Callable, Any
from aio_pika.channel import Channel
from aio_pika.message import IncomingMessage, Message, DeliveryMode, ReturnedMessage

from aio_pika.patterns.base import Proxy, Base


log = logging.getLogger(__name__)


class MasterWorker(Base):
    __slots__ = 'channel', 'loop', 'proxy', 'routes', 'queue'

    CONTENT_TYPE = 'application/python-pickle'
    DELIVERY_MODE = DeliveryMode.PERSISTENT

    __doc__ = """
    Implements Master/Worker pattern.
    Usage example:

    `subscriber.py` ::

        master = Master(channel)
        worker = await master.create_worker('test_worker', lambda x: print(x))

    `publisher.py` ::

        master = Master(channel)
        await master.proxy.test_worker('foo')
    """

    def __init__(self, channel: Channel, queue_name):
        """ Creates a new :class:`Master` instance.

        :param channel: Initialized instance of :class:`aio_pika.Channel`
        """
        self.channel = channel          # type: Channel
        self.loop = self.channel.loop   # type: asyncio.AbstractEventLoop
        self.proxy = Proxy(self.create_task)
        self.channel.add_on_return_callback(self.on_message_returned)

        self.routes = {}

        self.queue_name = queue_name
        self.queue = None

    @asyncio.coroutine
    def initialize_queue(self, **kwargs):
        self.queue = yield from self.channel.declare_queue(name=self.queue_name, **kwargs)

    def on_message_returned(self, message: ReturnedMessage):
        log.warning(
            "Message returned. Probably destination queue does not exists: %r",
            message
        )

    def serialize(self, data: Any) -> bytes:
        """ Serialize data to the bytes.
        Uses `pickle` by default.
        You should overlap this method when you want to change serializer

        :param data: Data which will be serialized
        :returns: bytes
        """
        return super().serialize(data)

    def deserialize(self, data: Any) -> bytes:
        """ Deserialize data from bytes.
        Uses `pickle` by default.
        You should overlap this method when you want to change serializer

        :param data: Data which will be deserialized
        :returns: :class:`Any`
        """
        return super().deserialize(data)

    @classmethod
    @asyncio.coroutine
    def execute(cls, func, kwargs):
        kwargs = kwargs or {}
        result = yield from func(**kwargs)
        return result

    @asyncio.coroutine
    def on_message(self, message: IncomingMessage):
        func_name = message.headers['FuncName']
        func = self.routes.get(func_name)
        if func:
            with message.process(requeue=True, ignore_processed=True):
                data = self.deserialize(message.body)
                yield from self.execute(func, data)

    @asyncio.coroutine
    def consume(self):
        yield from self.queue.consume(self.on_message)

    def create_work(self, func_name: str, func: Callable):
        """ Creates a new :class:`Worker` instance. """

        self.routes[func_name] = func

    @asyncio.coroutine
    def create_task(self, func_name: str, kwargs=None):
        """ Creates a new task for the worker """
        message = Message(
            body=self.serialize(kwargs or {}),
            content_type=self.CONTENT_TYPE,
            delivery_mode=self.DELIVERY_MODE,
            headers={
                'FuncName': func_name
            }
        )

        yield from self.channel.default_exchange.publish(
            message, self.queue_name, mandatory=True
        )
