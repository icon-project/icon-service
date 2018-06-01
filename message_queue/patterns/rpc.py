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
import pickle

import time
from typing import Callable, Any, TypeVar

from aio_pika.exchange import ExchangeType
from aio_pika.channel import Channel
from aio_pika.exceptions import UnroutableError
from aio_pika.message import Message, IncomingMessage, DeliveryMode, ReturnedMessage
from aio_pika.tools import create_future
from aio_pika.patterns.base import Proxy, Base

log = logging.getLogger(__name__)

R = TypeVar('R')
P = [TypeVar('P')]


class RPC(Base):
    __slots__ = ("channel", "loop", "proxy", "result_queue",
                 "result_consumer_tag", "routes", "consumer_tags",
                 "dlx_exchange",)

    DLX_NAME = 'rpc.dlx'

    __doc__ = """
    Remote Procedure Call helper.

    Create an instance ::

        rpc = await RPC.create(channel)

    Registering python function ::

        # RPC instance passes only keyword arguments
        def multiply(*, x, y):
            return x * y

        await rpc.register("multiply", multiply)

    Call function through proxy ::

        assert await rpc.proxy.multiply(x=2, y=3) == 6

    Call function explicit ::

        assert await rpc.call('multiply', dict(x=2, y=3)) == 6

    """

    def __init__(self, channel: Channel, queue_name):
        self.channel = channel
        self.loop = self.channel.loop
        self.proxy = Proxy(self.call)
        self.result_queue = None
        self.futures = dict()
        self.result_consumer_tag = None
        self.func_names = {}
        self.routes = {}

        self.queue_name = queue_name
        self.queue = None

        self.dlx_exchange = None

    def create_future(self) -> asyncio.Future:
        future = create_future(loop=self.loop)
        future_id = id(future)
        self.futures[future_id] = future
        future.add_done_callback(lambda f: self.futures.pop(future_id, None))
        return future

    def close(self) -> asyncio.Task:
        @asyncio.coroutine
        def closer():
            nonlocal self

            if self.result_queue is None:
                return

            for future in self.futures.values():
                future.set_exception(asyncio.CancelledError)

            yield from self.result_queue.unbind(
                self.dlx_exchange, "",
                arguments={
                    "From": self.result_queue.name,
                    'x-match': 'any',
                }
            )

            yield from self.result_queue.cancel(self.result_consumer_tag)
            self.result_consumer_tag = None

            yield from self.result_queue.delete()
            self.result_queue = None

        return self.loop.create_task(closer())

    @asyncio.coroutine
    def initialize(self, **kwargs):
        if self.result_queue is not None:
            return

        self.result_queue = yield from self.channel.declare_queue(None, auto_delete=True, **kwargs)

        self.dlx_exchange = yield from self.channel.declare_exchange(
            self.DLX_NAME,
            type=ExchangeType.HEADERS,
            auto_delete=True,
        )

        yield from self.result_queue.bind(
            self.dlx_exchange, "",
            arguments={
                "From": self.result_queue.name,
                'x-match': 'any',
            }
        )

        self.result_consumer_tag = yield from self.result_queue.consume(
            self.on_result_message, exclusive=True, no_ack=True
        )

        self.channel.add_on_return_callback(self.on_message_returned)

    @asyncio.coroutine
    def initialize_queue(self, **kwargs):
        arguments = kwargs.pop('arguments', {}).update({
            'x-dead-letter-exchange': self.DLX_NAME,
        })

        kwargs['arguments'] = arguments

        self.queue = yield from self.channel.declare_queue(name=self.queue_name, **kwargs)

    @classmethod
    @asyncio.coroutine
    def create(cls, channel: Channel, queue_name, **kwargs):
        """ Creates a new instance of :class:`aio_pika.patterns.RPC`.
        You should use this method instead of :func:`__init__`,
        because :func:`create` returns coroutine and makes async initialize

        :param channel: initialized instance of :class:`aio_pika.Channel`
        :returns: :class:`RPC`

        """
        rpc = cls(channel, queue_name)
        yield from rpc.initialize(**kwargs)
        return rpc

    def on_message_returned(self, message: ReturnedMessage):
        correlation_id = int(message.correlation_id) if message.correlation_id else None
        future = self.futures.pop(correlation_id, None)   # type: asyncio.Future

        if not future or future.done():
            log.warning("Unknown message was returned: %r", message)
            return

        future.set_exception(UnroutableError([message]))

    @asyncio.coroutine
    def on_result_message(self, message: IncomingMessage):
        correlation_id = int(message.correlation_id) if message.correlation_id else None
        future = self.futures.pop(correlation_id, None)  # type: asyncio.Future

        if future is None:
            log.warning("Unknown message: %r", message)
            return

        payload = self.deserialize(message.body)

        if message.type == 'result':
            future.set_result(payload)
        elif message.type == 'error':
            future.set_exception(payload)
        elif message.type == 'call':
            future.set_exception(
                asyncio.TimeoutError("Message timed-out", message)
            )
        else:
            future.set_exception(
                RuntimeError("Unknown message type %r" % message.type)
            )

    @asyncio.coroutine
    def on_call_message(self, message: IncomingMessage):
        func_name = message.headers['FuncName']
        if func_name not in self.routes:
            return

        payload = self.deserialize(message.body)
        func = self.routes[func_name]

        try:
            result = yield from self.execute(func, payload)
            result = self.serialize(result)
            message_type = 'result'
        except Exception as e:
            result = self.serialize_exception(e)
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

    def serialize_exception(self, exception: Exception) -> bytes:
        """ Serialize python exception to bytes

        :param exception: :class:`Exception`
        :return: bytes
        """
        return pickle.dumps(exception)

    @asyncio.coroutine
    def execute(self, func: Callable[P, R], payload: P) -> R:
        """ Executes rpc call. Might be overlapped. """
        return (yield from func(**payload))

    @asyncio.coroutine
    def call(self, func_name, kwargs: dict=None, *, expiration: int=None,
             priority: int=128, delivery_mode: DeliveryMode=DeliveryMode.NOT_PERSISTENT):

        """ Call remote method and awaiting result.

        :param func_name: Name of Function
        :param kwargs: Function kwargs
        :param expiration: If not `None` messages which staying in queue longer
                           will be returned and :class:`asyncio.TimeoutError` will be raised.
        :param priority: Message priority
        :param delivery_mode: Call message delivery mode
        :raises asyncio.TimeoutError: when message expired
        :raises CancelledError: when called :func:`RPC.cancel`
        :raises RuntimeError: internal error
        """

        future = self.create_future()

        message = Message(
            body=self.serialize(kwargs or {}),
            type='call',
            timestamp=time.time(),
            priority=priority,
            correlation_id=id(future),
            delivery_mode=delivery_mode,
            reply_to=self.result_queue.name,
            headers={
                'From': self.result_queue.name,
                'FuncName': func_name
            }
        )

        if expiration is not None:
            message.expiration = expiration

        yield from self.channel.default_exchange.publish(
            message, routing_key=self.queue_name, mandatory=True
        )

        return (yield from future)

    @asyncio.coroutine
    def consume(self):
        yield from self.queue.consume(self.on_call_message)

    def register(self, func_name, func: Callable[P, R]):
        """ Method creates a queue with name which equal of `func_name` argument.
        Then subscribes this queue.

        :param func_name: Function name
        :param func: target function. Function **MUST** accept only keyword arguments.
        :raises RuntimeError: Function already registered in this :class:`RPC` instance or
                              func_name already used.
        """

        if func_name in self.routes:
            raise RuntimeError(
                'Method name already used for %r' % self.routes[func_name]
            )

        self.func_names[func] = func_name
        self.routes[func_name] = asyncio.coroutine(func)

    def unregister(self, func):
        """ Cancels subscription to the method-queue.

        :param func: Function
        """

        func_name = self.func_names.pop(func)
        self.routes.pop(func_name)
