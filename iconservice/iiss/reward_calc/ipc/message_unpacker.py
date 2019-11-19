# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .message import *


class MessageUnpacker(object):
    def __init__(self):
        self._unpacker = msgpack.Unpacker(raw=True)
        self._iter = None
        self._response_classes = {
            MessageType.VERSION: VersionResponse,
            MessageType.CLAIM: ClaimResponse,
            MessageType.QUERY: QueryResponse,
            MessageType.CALCULATE: CalculateResponse,
            MessageType.COMMIT_BLOCK: CommitBlockResponse,
            MessageType.COMMIT_CLAIM: CommitClaimResponse,
            MessageType.QUERY_CALCULATE_STATUS: QueryCalculateStatusResponse,
            MessageType.QUERY_CALCULATE_RESULT: QueryCalculateResultResponse,
            MessageType.INIT: InitResponse,
            MessageType.READY: ReadyNotification,
            MessageType.CALCULATE_DONE: CalculateDoneNotification,
            MessageType.ROLLBACK: RollbackResponse,
        }

    def feed(self, data: bytes):
        self._unpacker.feed(data)

    def __iter__(self):
        self._iter = iter(self._unpacker)
        return self

    def __next__(self):
        try:
            message: list = next(self._iter)
            return self._parse(message)
        except:
            self._iter = None
            raise

    def _parse(self, message: list):
        msg_type: MessageType = MessageType(message[0])
        response_class = self._response_classes[msg_type]
        return response_class.from_list(message)
