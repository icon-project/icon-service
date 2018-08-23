# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

import hashlib


class Crypto:
    """Class for handling wrapping function about crypto
    """

    def __init__(self):
        pass
    
    @staticmethod
    def sha3_256(hash_data: bytes = None):
        return Sha3_256(hash_data)


class Sha3_256:
    def __init__(self, hash_data: bytes = None, hash_obj=None):
        if hash_obj is None:
            if hash_data is None:
                self._hash_obj = hashlib.sha3_256()
            else:
                self._hash_obj = hashlib.sha3_256(hash_data)
        else:
            self._hash_obj = hash_obj

    def update(self, args: bytes) -> None:
        self._hash_obj.update(args)

    def digest(self) -> bytes:
        return self._hash_obj.digest()

    def hexdigest(self) -> str:
        return self._hash_obj.hexdigest()

    def copy(self) -> 'Sha3_256':
        return Sha3_256(hash_obj=self._hash_obj.copy())
