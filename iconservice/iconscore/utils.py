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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base.address import Address


def get_package_name_by_address_and_tx_hash(address: 'Address', tx_hash: bytes) -> str:
    return f'{address.to_bytes().hex()}.0x{tx_hash.hex()}'


def get_score_deploy_path(score_root_path: str, score_address: 'Address', tx_hash: bytes) -> str:
    return os.path.join(score_root_path, score_address.to_bytes().hex(), f'0x{tx_hash.hex()}')

