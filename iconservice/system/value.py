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

from .listener import SystemValueListener
from .. import Address
from ..base.exception import AccessDeniedException
from ..icon_constant import SystemValueType, IconScoreContextType
from ..iconscore.icon_score_step import IconScoreStepCounter, StepType
from ..iconscore.icon_score_context import IconScoreContext
from ..utils.msgpack_for_db import MsgPackForDB

SystemRevision = namedtuple('SystemRevision', ['code', 'name'])


class SystemValueConverter(object):
    @staticmethod
    def convert_for_icon_service(type_: 'SystemValueType', value: Any) -> Any:
        """
        Convert system value data type for icon service.
        Some data need to be converted for enhancing efficiency.
        :param type_:
        :param value:
        :return:
        """
        converted_value: Any = value
        if type_ == SystemValueType.MAX_STEP_LIMITS:
            converted_value: dict = {}
            for key, value in value.items():
                if isinstance(key, IconScoreContextType):
                    converted_value[key] = value
                elif isinstance(key, int):
                    converted_value[IconScoreContextType(key)] = value
                elif isinstance(key, str):
                    if key == "invoke":
                        converted_value[IconScoreContextType.INVOKE] = value
                    elif key == "query":
                        converted_value[IconScoreContextType.QUERY] = value
                else:
                    raise ValueError(f"Invalid data type: "
                                     f"system value: {SystemValueType.name} "
                                     f"key type: {type(key)}")
        elif type_ == SystemValueType.STEP_COSTS:
            converted_value: dict = {}
            for key, value in value.items():
                if isinstance(key, StepType):
                    converted_value[key] = value
                elif isinstance(key, str):
                    try:
                        converted_value[StepType(key)] = value
                    except ValueError:
                        # Pass the unknown step type
                        pass
                else:
                    raise ValueError(f"Invalid data type: "
                                     f"system value: {SystemValueType.name} "
                                     f"key type: {type(key)}")
        return converted_value

    @staticmethod
    def convert_for_governance_score(type_: 'SystemValueType', value: Any) -> Any:
        """
        Convert system value data type for governance score
        Some data which have been converted for enhancing efficiency need to be converted.

        :param type_:
        :param value:
        :return:
        """
        converted_value: Any = value
        if type_ == SystemValueType.MAX_STEP_LIMITS:
            converted_value: dict = {}
            for key, value in value.items():
                assert isinstance(key, IconScoreContextType)
                converted_value[key.name.lower()] = value
        elif type_ == SystemValueType.STEP_COSTS:
            converted_value: dict = {}
            for key, value in value.items():
                assert isinstance(key, StepType)
                converted_value[key.value] = value
        return converted_value


class SystemValue(object):

    def __init__(self, is_migrated: bool):
        # Todo: consider if the compound data should be immutable
        # Todo: Freeze data
        # Todo: Consider about integrating set method
        # Todo: Integrate to revision
        self._is_migrated: bool = is_migrated
        self._listener: Optional['SystemValueListener'] = None
        self._batch: dict = {}

        self._service_config: Optional[int] = None

        self._step_price: Optional[int] = None
        self._step_costs: Optional[Dict['StepType', int]] = None
        self._max_step_limits: Optional[Dict['IconScoreContextType', int]] = None

        self._revision_code: Optional[int] = None
        self._revision_name: Optional[str] = None

        self._score_black_list: Optional[List['Address']] = None
        self._import_white_list: Optional[Dict[str, List[str]]] = None

    def add_listener(self, listener: 'SystemValueListener'):
        assert isinstance(listener, SystemValueListener)
        assert isinstance(listener, IconScoreContext)
        if listener.type not in (IconScoreContextType.INVOKE, IconScoreContextType.ESTIMATION):
            raise AccessDeniedException(f"Method not allowed: context={listener.type.name}")
        self._listener = listener

    @property
    def is_migrated(self) -> bool:
        return self._is_migrated

    @property
    def service_config(self) -> int:
        return self._batch.get(SystemValueType.SERVICE_CONFIG, self._service_config).value

    @property
    def step_price(self) -> int:
        return self._batch.get(SystemValueType.STEP_PRICE, self._step_price)

    @property
    def step_costs(self) -> Dict['StepType', int]:
        return self._batch.get(SystemValueType.STEP_COSTS, self._step_costs)

    @property
    def max_step_limits(self) -> Dict['IconScoreContextType', int]:
        return self._batch.get(SystemValueType.MAX_STEP_LIMITS, self._max_step_limits)

    @property
    def revision_code(self) -> int:
        return self._batch.get(SystemValueType.REVISION_CODE, self._revision_code)

    @property
    def revision_name(self) -> str:
        return self._batch.get(SystemValueType.REVISION_NAME, self._revision_name)

    @property
    def score_black_list(self) -> List['Address']:
        return self._batch.get(SystemValueType.SCORE_BLACK_LIST, self._score_black_list)

    @property
    def import_white_list(self) -> Dict[str, List[str]]:
        return self._batch.get(SystemValueType.IMPORT_WHITE_LIST, self._import_white_list)

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
        for type_, value in data.items():
            context.storage.system.put_value(context, type_, value)
        context.storage.system.put_migration_flag(context)
        self._batch["is_migrated"] = True

    def is_migration_succeed(self) -> bool:
        return self._batch.get("is_migrated", False)

    def update_migration(self):
        self._is_migrated = True

    def _set(self, type_: 'SystemValueType', value: Any):
        if type_ == SystemValueType.REVISION_CODE:
            self._revision_code = value
        elif type_ == SystemValueType.REVISION_NAME:
            self._revision_name = value
        elif type_ == SystemValueType.SCORE_BLACK_LIST:
            self._score_black_list = value
        elif type_ == SystemValueType.STEP_PRICE:
            self._step_price = value
        elif type_ == SystemValueType.STEP_COSTS:
            self._step_costs = value
        elif type_ == SystemValueType.MAX_STEP_LIMITS:
            self._max_step_limits = value
        elif type_ == SystemValueType.SERVICE_CONFIG:
            self._service_config = value
        elif type_ == SystemValueType.IMPORT_WHITE_LIST:
            self._import_white_list = value
        else:
            raise ValueError(f"Invalid value type: {type_.name}")
        if self._listener is not None:
            self._listener.update_system_value(type_, value)

    def set_by_icon_service(self, type_: 'SystemValueType', value: Any, is_open: bool = False):
        """
        Set value on system value instance from icon service.
        There are two cases of calling this method.
        First: Before migration
        Second: Initiating 'system value' when opening icon service (i.e. first initiation)

        :param type_:
        :param value:
        :param is_open:
        :return:
        """
        assert isinstance(type_, SystemValueType)
        if not self._is_migrated or is_open is True:
            self._set(type_, value)
        else:
            raise PermissionError(f"Invalid case of setting system value from icon-service"
                                  f"migration: {self._is_migrated} is open: {is_open}")

    def set_by_governance_score(self, context: 'IconScoreContext', type_: 'SystemValueType', value: Any):
        """
        Set values on system value and put these into DB.
        Only Governance Score can set values after migration.
        :param context:
        :param type_:
        :param value:
        :return:
        """
        assert self._is_migrated
        assert isinstance(type_, SystemValueType)
        # Update member variables
        # Check If value is valid
        self._batch[type_] = value
        context.storage.system.put_value(context, type_, value)

    @staticmethod
    def serialize_value_by_type(type_: 'SystemValueType', value: Any) -> bytes:
        version: int = 0
        if type_ == SystemValueType.MAX_STEP_LIMITS or type_ == SystemValueType.STEP_COSTS:
            value: dict = {key.value: value for key, value in value.items()}
        items: List[version, Any] = [version, value]
        return MsgPackForDB.dumps(items)

    @staticmethod
    def deserialize_value_by_type(type_: 'SystemValueType', value: bytes) -> Any:
        items: list = MsgPackForDB.loads(value)
        version: int = items[0]
        deserialized_value: Any = items[1]
        assert version == 0
        return SystemValueConverter.convert_for_icon_service(type_, deserialized_value)

    def is_updated(self) -> bool:
        return bool(len(self._batch))

    def update_batch(self):
        for type_, value in self._batch.items():
            self._set(type_, value)

    def clear_batch(self):
        self._batch.clear()

    def copy(self) -> 'SystemValue':
        """Copy system value"""
        return copy.copy(self)
