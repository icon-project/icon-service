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

import aio_pika
import asyncio

from typing import TypeVar, Generic

from message_queue import MessageQueueType, MESSAGE_QUEUE_TYPE_KEY, TASK_ATTR_DICT
from message_queue.patterns import MasterWorker, RPC

T = TypeVar('T')


class MessageQueueService(Generic[T]):
    TaskType: type = None

    loop = asyncio.get_event_loop() or asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def __init__(self, amqp_target, route_key, **task_kwargs):
        if self.TaskType is None:
            raise RuntimeError("MessageQueueTasks is not specified.")

        self._amqp_target = amqp_target
        self._route_key = route_key

        self._connection = None
        self._channel = None
        self._queue = None
        self._queue_consume_tag = None

        self._pattern_master_worker: MasterWorker = None
        self._pattern_rpc: RPC = None

        self._task = self.__class__.TaskType(**task_kwargs)

    async def connect(self, **kwargs):
        self._connection = await aio_pika.connect_robust(f"amqp://{self._amqp_target}")
        self._channel = await self._connection.channel()
        self._pattern_master_worker = MasterWorker(self._channel, self._route_key)
        self._pattern_rpc = await RPC.create(self._channel, self._route_key)

        await self._serve_tasks(**kwargs)

    async def _serve_tasks(self, **kwargs):
        for attribute_name in dir(self._task):
            try:
                attribute = getattr(self._task, attribute_name)
                task_attr: dict = getattr(attribute, TASK_ATTR_DICT)
            except AttributeError:
                pass
            else:
                func_name = f"{type(self._task).__name__}.{attribute_name}"

                message_queue_type = task_attr[MESSAGE_QUEUE_TYPE_KEY]
                if message_queue_type == MessageQueueType.MasterWorker:
                    self._pattern_master_worker.create_work(func_name, attribute)
                elif message_queue_type == MessageQueueType.RPC:
                    self._pattern_rpc.register(func_name, attribute)
                else:
                    raise RuntimeError(f"MessageQueueType invalid. {func_name}, {message_queue_type}")

        self._queue = await self._channel.declare_queue(self._route_key, auto_delete=True)
        self._queue_consume_tag = await self._queue.consume(self._consume, **kwargs)

    async def _consume(self, message):
        await self._pattern_master_worker.on_message(message)
        await self._pattern_rpc.on_call_message(message)

    def serve(self, **kwargs):
        self.loop.create_task(self.connect(**kwargs))

    @classmethod
    def serve_all(cls):
        cls.loop.run_forever()
