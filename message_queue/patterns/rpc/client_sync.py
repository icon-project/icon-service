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

import time

from concurrent import futures

from aio_pika import ExchangeType, Message, DeliveryMode
from aio_pika.patterns.base import Base


class ClientSync(Base):
    DLX_NAME = 'rpc.dlx'

    def __init__(self, channel, queue_name):
        self.channel = channel
        self.queue_name = queue_name
        self.result_queue_name = None

        self.futures = {}

        self.func_names = {}
        self.routes = {}

        self.dlx_exchange = None

    def initialize_exchange(self):
        self.dlx_exchange = self.channel.exchange_declare(
            exchange=self.DLX_NAME,
            exchange_type=ExchangeType.HEADERS.value,
            auto_delete=True,
        )

    def initialize_queue(self, **kwargs):
        arguments = kwargs.pop('arguments', {}).update({
            'x-dead-letter-exchange': self.DLX_NAME,
        })

        kwargs['arguments'] = arguments

        self.channel.queue_declare(queue=self.queue_name, **kwargs)
        self.result_queue_name = self.channel.queue_declare(exclusive=True, auto_delete=True).method.queue

        self.channel.queue_bind(
            queue=self.queue_name,
            exchange=self.DLX_NAME,
            arguments={
                "From": self.result_queue_name,
                'x-match': 'any',
            }
        )
        self.channel.basic_consume(self._on_result_message, queue=self.result_queue_name, no_ack=True)

    def _on_result_message(self, channel, method, properties, body):
        correlation_id = int(properties.correlation_id)
        try:
            future = self.futures[correlation_id]
        except KeyError:
            pass
        else:
            payload = self.deserialize(body)
            future.set_result(payload)

    def call(self, func_name, kwargs: dict=None, *, expiration: int=None,
             priority: int=128, delivery_mode: DeliveryMode=DeliveryMode.NOT_PERSISTENT):
        future = self._create_future()
        correlation_id = id(future)

        message = Message(
            body=self.serialize(kwargs or {}),
            type='call',
            timestamp=time.time(),
            expiration=expiration,
            priority=priority,
            correlation_id=correlation_id,
            delivery_mode=delivery_mode,
            reply_to=self.result_queue_name,
            headers={
                'From': self.result_queue_name,
                'FuncName': func_name
            },
        )

        # noinspection PyProtectedMember
        self.channel.basic_publish(
            '', self.queue_name, message.body, message.properties, mandatory=True
        )

        while not future.done():
            self.channel.connection.process_data_events()

        if future.exception():
            return future.exception()
        else:
            return future.result()

    def _create_future(self) -> futures.Future:
        future = futures.Future()
        future_id = id(future)
        self.futures[future_id] = future
        future.add_done_callback(lambda f: self.futures.pop(future_id, None))
        return future
