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
import functools
import inspect
import logging

from typing import TypeVar, Generic
from message_queue import MessageQueueType, MessageQueueException, MESSAGE_QUEUE_TYPE_KEY, TASK_ATTR_DICT
from message_queue import MasterWorker, RPC

T = TypeVar('T')


class MessageQueueStub(Generic[T]):
    TaskType: type = None

    def __init__(self, amqp_target, route_key):
        if self.TaskType is None:
            raise RuntimeError("MessageQueueTasks is not specified.")

        self._amqp_target = amqp_target
        self._route_key = route_key

        self._connection = None
        self._channel = None

        self._pattern_master_worker: MasterWorker = None
        self._pattern_rpc: RPC = None

        self._task = object.__new__(self.__class__.TaskType)  # not calling __init__

    async def connect(self):
        self._connection = await aio_pika.connect(f"amqp://{self._amqp_target}")
        self._channel = await self._connection.channel()

        self._pattern_master_worker = MasterWorker(self._channel, self._route_key)
        self._pattern_rpc = await RPC.create(self._channel, self._route_key)

        await self._pattern_master_worker.initialize_queue(auto_delete=True)
        await self._pattern_rpc.initialize_queue(auto_delete=True)

        await self._register_tasks()

    async def _register_tasks(self):
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
                    binding_method = self._call_task
                elif message_queue_type == MessageQueueType.RPC:
                    binding_method = self._call_rpc
                else:
                    raise RuntimeError(f"MessageQueueType invalid. {func_name}, {message_queue_type}")

                stub = functools.partial(binding_method, func_name, attribute)
                setattr(self._task, attribute_name, stub)

    async def _call_task(self, func_name, func, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        await self._pattern_master_worker.create_task(func_name, kwargs=params.arguments)

    async def _call_rpc(self, func_name, func, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        result = await self._pattern_rpc.call(func_name, kwargs=params.arguments)
        if isinstance(result, MessageQueueException):
            logging.error(result)
            raise result
        return result

    def task(self) -> T:
        return self._task
