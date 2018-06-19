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

import time

from aio_pika.message import Message, DeliveryMode
from aio_pika.patterns.base import Base
from pika.adapters.blocking_connection import BlockingChannel


class ClientSync(Base):
    CONTENT_TYPE = 'application/python-pickle'
    DELIVERY_MODE = DeliveryMode.PERSISTENT

    def __init__(self, channel: BlockingChannel, queue_name):
        self.channel = channel
        self.queue_name = queue_name

    def initialize_queue(self, **kwargs):
        self.channel.queue_declare(queue=self.queue_name, **kwargs)

    def call(self, func_name: str, kwargs=None, priority=128):
        message = Message(
            body=self.serialize(kwargs or {}),
            content_type=self.CONTENT_TYPE,
            delivery_mode=self.DELIVERY_MODE,
            priority=priority,
            headers={
                'FuncName': func_name
            }
        )

        # noinspection PyProtectedMember
        self.channel.basic_publish(
            '',
            self.queue_name,
            message.body,
            message.properties,
        )
