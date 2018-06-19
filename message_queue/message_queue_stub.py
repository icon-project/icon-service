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
import pika

from typing import TypeVar, Generic
from message_queue import (
    MessageQueueType, MessageQueueException, worker, rpc,
    MESSAGE_QUEUE_TYPE_KEY, MESSAGE_QUEUE_PRIORITY_KEY, TASK_ATTR_DICT)


T = TypeVar('T')


class MessageQueueStub(Generic[T]):
    TaskType: type = None

    def __init__(self, amqp_target, route_key):
        if self.TaskType is None:
            raise RuntimeError("MessageQueueTasks is not specified.")

        self._amqp_target = amqp_target
        self._route_key = route_key

        self._worker_client_async: worker.ClientAsync = None
        self._worker_client_sync: worker.ClientSync = None

        self._rpc_client_async: rpc.ClientAsync = None
        self._rpc_client_sync: rpc.ClientSync = None

        self._sync_task = object.__new__(self.__class__.TaskType)  # not calling __init__
        self._async_task = object.__new__(self.__class__.TaskType)  # not calling __init__

    async def connect(self):
        await self.connect_async()
        self.connect_sync()

        await self._register_tasks()

    async def connect_async(self):
        connection = await aio_pika.connect(f"amqp://{self._amqp_target}")
        channel = await connection.channel()

        self._worker_client_async = worker.ClientAsync(channel, self._route_key)
        await self._worker_client_async.initialize_queue(auto_delete=True)

        self._rpc_client_async = rpc.ClientAsync(channel, self._route_key)
        await self._rpc_client_async.initialize_exchange()
        await self._rpc_client_async.initialize_queue(auto_delete=True)

    def connect_sync(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=f'{self._amqp_target}'))
        channel = connection.channel()

        self._worker_client_sync = worker.ClientSync(channel, self._route_key)
        self._worker_client_sync.initialize_queue(auto_delete=True)

        self._rpc_client_sync: rpc.ClientSync = rpc.ClientSync(channel, self._route_key)
        self._rpc_client_sync.initialize_exchange()
        self._rpc_client_sync.initialize_queue(auto_delete=True)

    async def _register_tasks(self):
        for attribute_name in dir(self._async_task):
            try:
                attribute = getattr(self._async_task, attribute_name)
                task_attr: dict = getattr(attribute, TASK_ATTR_DICT)
            except AttributeError:
                pass
            else:
                func_name = f"{type(self._async_task).__name__}.{attribute_name}"

                message_queue_type = task_attr[MESSAGE_QUEUE_TYPE_KEY]
                message_queue_priority = task_attr[MESSAGE_QUEUE_PRIORITY_KEY]
                if message_queue_type == MessageQueueType.Worker:
                    binding_async_method = self._call_async_worker
                    binding_sync_method = self._call_sync_worker
                elif message_queue_type == MessageQueueType.RPC:
                    binding_async_method = self._call_async_rpc
                    binding_sync_method = self._call_sync_rpc
                else:
                    raise RuntimeError(f"MessageQueueType invalid. {func_name}, {message_queue_type}")

                stub = functools.partial(binding_async_method, func_name, attribute, message_queue_priority)
                setattr(self._async_task, attribute_name, stub)

                stub = functools.partial(binding_sync_method, func_name, attribute, message_queue_priority)
                setattr(self._sync_task, attribute_name, stub)

    async def _call_async_worker(self, func_name, func, priority, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        await self._worker_client_async.call(func_name, kwargs=params.arguments, priority=priority)

    async def _call_async_rpc(self, func_name, func, priority, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        result = await self._rpc_client_async.call(func_name, kwargs=params.arguments, priority=priority)
        if isinstance(result, MessageQueueException):
            logging.error(result)
            raise result
        return result

    def _call_sync_worker(self, func_name, func, priority, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        self._worker_client_sync.call(func_name, kwargs=params.arguments, priority=priority)

    def _call_sync_rpc(self, func_name, func, priority, *args, **kwargs):
        params = inspect.signature(func).bind(*args, **kwargs)
        params.apply_defaults()
        result = self._rpc_client_sync.call(func_name, kwargs=params.arguments, priority=priority)
        if isinstance(result, MessageQueueException):
            logging.error(result)
            raise result
        return result

    def async_task(self) -> T:
        return self._async_task

    def sync_task(self) -> T:
        return self._sync_task
