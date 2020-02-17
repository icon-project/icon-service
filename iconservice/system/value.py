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
from collections import namedtuple
from typing import TYPE_CHECKING, Any, Dict, Optional, List

from .. import Address
from ..iconscore.icon_score_step import IconScoreStepCounter


if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icon_constant import SystemValueType, IconScoreContextType, Revision
    from .listener import SystemValueListener
    from ..system import SystemStorage


SystemRevision = namedtuple('SystemRevision', ['code', 'name'])
ImportWhiteList = namedtuple('ImportWhiteList', ['white_list', 'keys'])


class SystemValue:

    def __init__(self, is_migrated: bool):
        # Todo: consider if the compound data should be immutable
        # Todo: consider about transaction failure
        self._is_migrated: bool = is_migrated
        self._listener: Optional['SystemValueListener'] = None

        self._service_config: Optional[int] = None
        self._deployer_list: Optional[List['Address']] = None

        # Todo: raise Exception when trying to get variable which is not set (i.e. None)
        self._step_price: Optional[int] = None
        self._step_costs: Optional[dict] = None
        self._max_step_limits: Optional[dict] = None

        # Todo: Integrate to revision
        self._revision_code: Optional[Revision] = None
        self._revision_name: Optional[str] = None

        self._score_black_list: Optional[list] = None
        self._import_white_list: Optional[list] = None

    # Todo: should change type hint to 'IconScoreContext'? and should check if context.type is invoke?
    def add_listener(self, listener: 'SystemValueListener'):
        assert isinstance(listener, SystemValueListener)
        self._listener = listener

    @property
    def is_migrated(self):
        return self._is_migrated

    @property
    def service_config(self):
        return self._service_config

    @property
    def deployer_list(self):
        return self._deployer_list

    @property
    def step_price(self):
        return self._step_price

    @property
    def step_costs(self):
        return self._step_costs

    @property
    def max_step_limits(self):
        return self._max_step_limits

    @property
    def revision_code(self):
        return self._revision_code

    @property
    def revision_name(self):
        return self._revision_name

    @property
    def score_black_list(self):
        return self._score_black_list

    @property
    def import_white_list(self):
        return self._import_white_list

    def create_step_counter(self,
                            context_type: 'IconScoreContextType',
                            step_trace_flag: bool) -> 'IconScoreStepCounter':
        step_price: int = self._step_price
        # Copying a `dict` so as not to change step costs when processing a transaction.
        step_costs: dict = self._step_costs.copy()
        max_step_limit: int = self._max_step_limits.get(context_type, 0)

        return IconScoreStepCounter(step_price, step_costs, max_step_limit, step_trace_flag)

    def migrate(self, context: 'IconScoreContext', data: Dict['SystemValueType', Any]):
        """
        Migrates governance variablie from Governance score to Governance Value.
        It will be called when updating governance score to version "".
        This method is called only once.
        :param context:
        :param data:
        :return:
        """
        for key, value in data.items():
            context.storage.system.put_value(context, key.value, value)
        context.storage.system.put_migration_flag(context)
        self._is_migrated = True

    def _set(self, value_type: 'SystemValueType', value: Any):
        if value_type == SystemValueType.REVISION_CODE:
            self._revision_code = Revision(value)
        elif value_type == SystemValueType.SCORE_BLACK_LIST:
            self._score_black_list = value
        elif value_type == SystemValueType.STEP_PRICE:
            self._step_price = value
        elif value_type == SystemValueType.STEP_COSTS:
            self._step_costs = value
        elif value_type == SystemValueType.MAX_STEP_LIMITS:
            self._max_step_limits = value
        elif value_type == SystemValueType.SERVICE_CONFIG:
            self._service_config = value
        elif value_type == SystemValueType.IMPORT_WHITE_LIST:
            self._import_white_list = value
        else:
            raise ValueError(f"Invalid value type: {value_type.name}")
        if self._listener is not None:
            self._listener.update(value_type, value)

    #Todo: set method 통합
    def set_from_icon_service(self, value_type: 'SystemValueType', value: Any, is_open: bool = False):
        """
        Set value on system value instance from icon service.
        There are two cases of calling this method.
        First: Before migration
        Second: Initiating 'system value' when opening icon service (i.e. first initiation)

        :param value_type:
        :param value:
        :param is_open:
        :return:
        """
        assert isinstance(value_type, SystemValueType)
        if not self._is_migrated or is_open is True:
            self._set(value_type, value)
        else:
            raise PermissionError(f"Invalid case of setting system value from icon-service"
                                  f"migration: {self._is_migrated} is open: {is_open}")

    def set_from_governance_score(self, context: 'IconScoreContext', value_type: 'SystemValueType', value: Any):
        """
        Set values on system value and put these into DB.
        Only Governance Score can set values after migration.
        :param context:
        :param value_type:
        :param value:
        :return:
        """
        # Todo: Only GS can access. IS can not call directly (Inspect caller)
        assert self._is_migrated
        assert isinstance(value_type, SystemValueType)
        # Update member variables
        # Check If value is valid
        self._set(value_type, value)
        context.storage.system.put_value(context, value_type, value)

    def copy(self):
        """Copy system value"""
        return copy.copy(self)
