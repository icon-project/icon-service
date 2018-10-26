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
import os
import time

from iconservice import Address


class DirectoryNameConverter:
    counter = 0

    @classmethod
    def rename_directory(cls, path: str):
        if os.path.exists(path):
            cls.counter += 1
            os.rename(path, f"{path}{int(time.time()*10**6)}{cls.counter}_garbage_score")

    @staticmethod
    def get_score_path_by_address_and_tx_hash(score_root: str, address: 'Address', tx_hash: bytes):
        score_root_path = os.path.join(score_root, address.to_bytes().hex())
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        install_path = os.path.join(score_root_path, converted_tx_hash)
        return install_path
