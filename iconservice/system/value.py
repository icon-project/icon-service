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
import copy
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
        # Todo: consider if the compound data should be immutable
        self._is_migrated: bool = is_migrated

        self._step_price: int = step_price
        self._step_costs: dict = step_costs
        self._max_step_limits: dict = max_step_limits

        self._revision_code: int = revision_code
        self._revision_name: str = revision_name

        self._score_black_list: list = score_black_list
        self._import_white_list: list = import_white_list
        self._import_white_list_keys: str = import_white_list_key

        self._set_value_mapper = {
            SystemValueType.STEP_PRICE: self._set_step_price,
            SystemValueType.STEP_COSTS: self._set_step_costs,
            SystemValueType.MAX_STEP_LIMITS: self._set_max_step_limits,
            SystemValueType.REVISION_CODE: self._set_revision_code,
            SystemValueType.REVISION_NAME: self._set_revision_name,
            SystemValueType.SCORE_BLACK_LIST: self._set_score_black_list,
            SystemValueType.IMPORT_WHITE_LIST: self._set_import_white_list,
            SystemValueType.IMPORT_WHITE_LIST_KEYS: self._set_import_white_list_keys,
        }

    @property
    def step_price(self):
        return self._step_price

    def _set_step_price(self, step_price: int):
        self._step_price: int = step_price

    @property
    def step_costs(self):
        return self._step_costs

    def _set_step_costs(self, step_costs: int):
        self._step_costs: int = step_costs

    @property
    def max_step_limits(self):
        return self._max_step_limits

    def _set_max_step_limits(self, max_step_limits: dict):
        self._max_step_limits: dict = max_step_limits

    @property
    def revision_code(self):
        return self._revision_code

    def _set_revision_code(self, revision_code: int):
        self._revision_code: int = revision_code

    @property
    def revision_name(self):
        return self._revision_name

    def _set_revision_name(self, revision_name: str):
        self._revision_name: str = revision_name

    @property
    def score_black_list(self):
        return self._score_black_list

    def _set_score_black_list(self, score_black_list: list):
        self._score_black_list: list = score_black_list

    @property
    def import_white_list(self):
        return self._import_white_list

    def _set_import_white_list(self, import_white_list: list):
        self._import_white_list: list = import_white_list

    @property
    def import_white_list_keys(self):
        return self._import_white_list_keys

    def _set_import_white_list_keys(self, import_white_list_keys: str):
        self._import_white_list_keys: str = import_white_list_keys

    def create_step_counter(self,
                            context_type: 'IconScoreContextType',
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
        for key, value in data.items():
            SystemStorage.put_value(context, key.value, value)
        SystemStorage.put_migration_flag(context)
        self._is_migrated = True

    def _set_value(self, value_type: 'SystemValueType', value: Any):
        self._set_value_mapper[value_type](value)

    def set_value_before_migration(self):
        """

        :return:
        """
        assert not self._is_migrated
        # Update member variables before migrations.
        # Must not put data to DB before migrations (only update member variables)
        # get all data from the governance score
        # update member variables

    def set_value_after_migration(self, context: 'IconScoreContext', value_type: 'SystemValueType', value: Any):
        """

        :param context:
        :param value_type:
        :param value:
        :return:
        """
        # Todo: Only GS can access. IS can not call directly
        assert self._is_migrated
        assert isinstance(value_type, SystemValueType)
        # Update member variables
        # Check If value is valid
        self._set_value(value_type, value)
        SystemStorage.put_value(context, value_type, value)

    def copy(self):
        """Copy governance value"""
        return copy.copy(self)
