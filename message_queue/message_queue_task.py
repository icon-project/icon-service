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

import asyncio
import functools
import logging
import traceback

from enum import IntEnum

TASK_ATTR_DICT = "task_attr"
MESSAGE_QUEUE_TYPE_KEY = "type"
MESSAGE_QUEUE_PRIORITY_KEY = "priority"


class MessageQueueType(IntEnum):
    Worker = 0,
    RPC = 1,


class MessageQueueException(Exception):
    pass


def message_queue_task(func=None, *, type_=MessageQueueType.RPC, priority=128):
    if func is None:
        return functools.partial(message_queue_task, type_=type_, priority=priority)

    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        try:
            return await asyncio.coroutine(func)(*args, **kwargs)
        except Exception as e:
            logging.error(e)
            traceback.print_exc()
            return MessageQueueException(str(e))

    task_attr = {
        MESSAGE_QUEUE_TYPE_KEY: type_,
        MESSAGE_QUEUE_PRIORITY_KEY: priority
    }
    setattr(_wrapper, TASK_ATTR_DICT, task_attr)
    return _wrapper
