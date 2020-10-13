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


"""iconservice unittest package
"""

import hashlib
import os
import random
import shutil
import sys
from time import time

from iconcommons.logger import Logger
from iconservice.base.address import Address, AddressPrefix
from iconservice.icon_constant import DATA_BYTE_ORDER
from iconservice.iconscore.internal_call import InternalCall
from iconservice.icx.unstake_patcher import INVALID_EXPIRED_UNSTAKES_FILENAME

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))

OTHER_CALL = InternalCall._other_score_call


def create_address(prefix: int = 0, data: bytes = None) -> 'Address':
    if data is None:
        data = create_tx_hash()
    hash_value = hashlib.sha3_256(data).digest()
    return Address(AddressPrefix(prefix), hash_value[-20:])


def create_hash_256(data: bytes = None) -> bytes:
    if data is None:
        max_int = sys.maxsize
        length = (max_int.bit_length() + 7) // 8
        data = int(random.randint(0, max_int)).to_bytes(length, DATA_BYTE_ORDER)

    return hashlib.sha3_256(data).digest()


def create_tx_hash(data: bytes = None) -> bytes:
    return create_hash_256(data)


def create_block_hash(data: bytes = None) -> bytes:
    return create_tx_hash(data)


def raise_exception_start_tag(tag: str = ""):
    emblem_str = '=' * 20
    Logger.error(f'{emblem_str} [{tag}] raise exception start {emblem_str}')


def raise_exception_end_tag(tag: str = ""):
    emblem_str = '=' * 20
    Logger.error(f'{emblem_str} [{tag}] raise exception end {emblem_str}')


def get_score_path(score_root: str, package_name: str):
    return os.path.join(TEST_ROOT_PATH, 'integrate_test/samples', score_root, package_name)


def rmtree(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


def root_clear(score_path: str, state_db_path: str, iiss_db_path: str, precommit_log_path: str):
    rmtree(score_path)
    rmtree(state_db_path)
    rmtree(iiss_db_path)
    rmtree(precommit_log_path)


def remove_unstake_report():
    names = INVALID_EXPIRED_UNSTAKES_FILENAME.split(".")
    log_dir = "."
    report_path: str = os.path.join(log_dir, f"{names[0]}_report.json")
    if os.path.isfile(report_path):
        os.remove(report_path)


def create_timestamp():
    return int(time() * 10 ** 6)
