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

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .data.candidate import Candidate


class Term(object):
    """Defines P-Rep Term information

    """

    def __init__(self):
        self.sequence: int = -1
        self.start_block_height: int = -1
        self.end_block_height: int = -1  # inclusive
        self.preps: List['Candidate'] = []

    def load(self, context: 'IconScoreContext'):
        pass
