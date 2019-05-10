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

from typing import Optional

from ..iconscore.icon_score_context import IconScoreContext
from ..base.exception import MethodNotFoundException


class Engine(object):
    def __init__(self):
        self._handler = {
            "ise_getPreps": self._handle_get_preps
        }

    def query(self, context: 'IconScoreContext', request: dict) -> dict:
        method: str = request["method"]
        params: Optional[dict] = request.get("params")

        if method in self._handler:
            raise MethodNotFoundException(f"Method not found: {method}")

        return self._handler[method](context, params)

    @staticmethod
    def _handle_get_preps(context: 'IconScoreContext', params: dict) -> dict:
        public_key: bytes = bytes.fromhex("1234567890abcdef")

        return {
            "result": {
                "blockHeight": 1028,
                "preps": [
                    {
                        "id": "hx86aba2210918a9b116973f3c4b27c41a54d5dafe",
                        "publicKey": public_key,
                        "url": "target://210.34.56.17:7100"
                    },
                    {
                        "id": "hx86aba2210918a9b116973f3c4b27c41a54d5dafe",
                        "publicKey": public_key,
                        "url": "target://210.34.56.17:7100"
                    }
                ]
            }
        }
