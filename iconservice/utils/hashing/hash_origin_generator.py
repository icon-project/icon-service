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

import abc


class HashOriginGenerator(abc.ABC):
    version = None

    @abc.abstractmethod
    def generate(self, origin_data: dict) -> str:
        pass


class HashOriginGeneratorV1(HashOriginGenerator):
    version = 1

    _translator = str.maketrans({
        "\\": "\\\\",
        "{": "\\{",
        "}": "\\}",
        "[": "\\[",
        "]": "\\]",
        ".": "\\."
    })

    def generate(self, json_data: dict):

        def encode(data):
            if isinstance(data, dict):
                return encode_dict(data)
            elif isinstance(data, list):
                return encode_list(data)
            else:
                return escape(data)

        def encode_dict(data: dict):
            result = ".".join(_encode_dict(data))
            return "{" + result + "}"

        def _encode_dict(data: dict):
            for key in sorted(data.keys()):
                yield key
                yield encode(data[key])

        def encode_list(data: list):
            result = ".".join(_encode_list(data))
            return f"[" + result + "]"

        def _encode_list(data: list):
            for item in data:
                yield encode(item)

        def escape(data):
            if data is None:
                return "\\0"

            data = str(data)
            return data.translate(self._translator)

        return ".".join(_encode_dict(json_data))
