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


from typing import TYPE_CHECKING, Any, Dict


from ..iconscore.icon_score_step import IconScoreStepCounter
from ..system import SystemStorage

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icon_constant import SystemValueType, IconScoreContextType


class SystemValue:

    def __init__(self,
                 is_migrated: bool,
                 step_price: int,
                 step_costs: dict,
                 max_step_limits: dict,
                 revision_code: int,
                 revision_name: str,
                 score_black_list: list,
                 import_white_list: list,
                 import_white_list_key: str):
        self._is_migrated: bool = is_migrated

        self._step_price = step_price
        self._step_costs = step_costs
        self._max_step_limits = max_step_limits

        self._revision_code = revision_code
        self._revision_name = revision_name

        self._score_black_list = score_black_list
        self._import_white_list = import_white_list
        self._import_white_list_keys = import_white_list_key

    @property
    def step_price(self):
        return self._step_price

    # Todo: Implement all property

    def create_step_counter(self, context_type: 'IconScoreContextType',
                            step_trace_flag: bool) -> 'IconScoreStepCounter':
        step_price: int = self._step_price
        # Copying a `dict` so as not to change step costs when processing a transaction.
        step_costs: dict = self._step_costs.copy()
        max_step_limit: int = self._max_step_limits.get(context_type, 0)

        return IconScoreStepCounter(step_price, step_costs, max_step_limit, step_trace_flag)

    def migrates(self, context: 'IconScoreContext', data: Dict['SystemValueType', Any]):
        """
        Migrates governance variablie from Governance score to Governance Value.
        It will be called when updating governance score to version "".
        This method is called only once.
        :param context:
        :param data:
        :return:
        """
        # get GV from the GS and put to the statedb

        # change the flag to migrates and put this state to the db

        for key, value in data.items():
            SystemStorage.put_value(context, key.value, value)
        SystemStorage.put_migration_flag(context)
        self._is_migrated = True

    def update_value_before_migration(self):
        assert not self._is_migrated
        # Update member variables before migrations.

        # Must not put data to DB before migrations (only update member variables)
        # get governance score and all data from it
        # update member variables

    def put_value(self, context: 'IconScoreContext', value_type: 'SystemValueType', value: Any):
        # Todo: Only GS can access. IS can not call directly
        assert self._is_migrated

        # Todo: convert value to bytes

    def copy(self):
        """Copy governance value"""
        pass
