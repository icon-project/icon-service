# Copyright 2019 ICON Foundation
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

from typing import TYPE_CHECKING

from ...database.db import ContextDatabase

from .iiss_common_variable import IissCommonVariable
from .iiss_issue_variable import IissIssueVariable

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext
    from iconcommons import IconConfig


class IissVariable(object):

    def __init__(self, db: 'ContextDatabase'):
        self._common: 'IissCommonVariable' = IissCommonVariable(db)
        self._issue: 'IissIssueVariable' = IissIssueVariable(db)

    def init_config(self, context: 'IconScoreContext', conf: 'IconConfig'):
        self._common.init_config(context, conf)
        self._issue.init_config(context, conf)

    @property
    def common(self) -> 'IissCommonVariable':
        return self._common

    @property
    def issue(self) -> 'IissIssueVariable':
        return self._issue
