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

from collections import OrderedDict
from enum import Enum


class BatchSlotType(Enum):
    PUT = 0
    UPDATE = 1


class CandidateBatch(OrderedDict):
    pass


class RegPRep(object):
    def __init__(self):
        pass


class UpdatePRep(object):
    def __init__(self, total_delegated: int):
        self.total_delegated: int = total_delegated


class UnregPRep(object):
    def __init__(self):
        pass
