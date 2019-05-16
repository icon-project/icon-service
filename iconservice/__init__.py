# Copyright 2018 ICON Foundation
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
"""Package for objects which are related with Icon Services"""

from abc import ABCMeta, abstractmethod, ABC
from functools import wraps
from inspect import isfunction

from iconcommons.logger import Logger

from .base.address import Address, AddressPrefix, ZERO_SCORE_ADDRESS
from .base.exception import IconScoreException
from .icon_constant import IconServiceFlag
from .iconscore.icon_container_db import VarDB, DictDB, ArrayDB
from .iconscore.icon_score_base import interface, eventlog, external, payable, IconScoreBase, IconScoreDatabase
from .iconscore.icon_score_base2 import InterfaceScore, revert, sha3_256, json_loads, json_dumps
from .iconscore.icon_score_base2 import recover_key, create_address_with_key
from .iconscore.icon_system_score_base import IconSystemScoreBase
