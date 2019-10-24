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

import copy
import hashlib
from typing import Union, Iterable

from .hash_origin_generator import HashOriginGeneratorV1
from .merkle_tree import MerkleTree


class HashGenerator:
    _SALT = "icx_sendTransaction"
    _ORIGIN_GENERATOR = HashOriginGeneratorV1()

    @classmethod
    def generate_origin(cls, origin_data: dict) -> str:
        copied_origin_data = copy.deepcopy(origin_data)
        return cls._ORIGIN_GENERATOR.generate(copied_origin_data)

    @classmethod
    def generate_salted_origin(cls, origin_data: dict) -> str:
        def _gen():
            if HashGenerator._SALT is not None:
                yield HashGenerator._SALT
            yield cls.generate_origin(origin_data)
        return '.'.join(_gen())

    @classmethod
    def generate_hash(cls, origin_data: dict) -> bytes:
        origin = cls.generate_salted_origin(origin_data)
        return hashlib.sha3_256(origin.encode()).digest()


class RootHashGenerator:
    @classmethod
    def generate_root_hash(cls, values: Union[Iterable, bytes, bytearray], do_hash=False) -> bytes:
        merkle_tree = MerkleTree()
        merkle_tree.add_leaf(values, do_hash)
        merkle_tree.make_tree()
        return merkle_tree.get_merkle_root()
