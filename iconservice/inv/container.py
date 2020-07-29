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
from typing import Any, Dict, List

from .data.value import Value, VALUE_MAPPER
from .. import Address
from ..base.exception import InvalidParamsException
from ..icon_constant import IconNetworkValueType, IconScoreContextType
from ..iconscore.icon_score_step import StepType

SystemRevision = namedtuple('SystemRevision', ['code', 'name'])


class ValueConverter(object):
    @staticmethod
    def convert_for_icon_service(type_: 'IconNetworkValueType', value: Any) -> 'Value':
        """
        Convert IconNetwork value data type for icon service.
        Some data need to be converted for enhancing efficiency.
        :param type_:
        :param value:
        :return:
        """
        converted_value: Any = value
        if type_ == IconNetworkValueType.MAX_STEP_LIMITS:
            converted_value: dict = {}
            for key, value in value.items():
                if isinstance(key, str):
                    if key == "invoke":
                        converted_value[IconScoreContextType.INVOKE] = value
                    elif key == "query":
                        converted_value[IconScoreContextType.QUERY] = value
                    else:
                        raise InvalidParamsException(f"Invalid context type: {type_.name}")
                else:
                    raise ValueError(f"Invalid data type: "
                                     f"value: {type_.name} "
                                     f"key type: {type(key)}")
        elif type_ == IconNetworkValueType.STEP_COSTS:
            converted_value: dict = {}
            for key, value in value.items():
                if isinstance(key, str):
                    try:
                        converted_value[StepType(key)] = value
                    except ValueError:
                        # Pass the unknown step type
                        pass
                else:
                    raise ValueError(f"Invalid data type: "
                                     f"value: {type_.name} "
                                     f"key type: {type(key)}")
        try:
            value: 'Value' = VALUE_MAPPER[type_](converted_value)
        except KeyError:
            raise InvalidParamsException(f"Invalid INV key: {type_}")

        return value

    @staticmethod
    def convert_for_governance(type_: 'IconNetworkValueType', value: Any) -> Any:
        """
        Convert IconNetwork value data type for governance score
        Some data which have been converted for enhancing efficiency need to be converted.

        :param type_:
        :param value:
        :return:
        """
        converted_value: Any = value
        if type_ == IconNetworkValueType.MAX_STEP_LIMITS:
            converted_value: dict = {}
            for key, value in value.items():
                assert isinstance(key, IconScoreContextType)
                converted_value[key.name.lower()] = value
        elif type_ == IconNetworkValueType.STEP_COSTS:
            converted_value: dict = {}
            for key, value in value.items():
                assert isinstance(key, StepType)
                converted_value[key.value] = value
        return converted_value


class Container(object):
    class BatchDict(dict):
        def __init__(self):
            super().__init__()
            self._migration_trigger: bool = False

        def __setitem__(self, key, value):
            if value is None:
                return
            if not isinstance(key, IconNetworkValueType) or key not in IconNetworkValueType:
                raise ValueError(f"Invalid value key: {key}")
            if not isinstance(value, Value):
                raise ValueError(f"Invalid value type: {type(value)}")

            super().__setitem__(key, value)

        def trigger_migration(self):
            self._migration_trigger: bool = True

        def is_migration_triggered(self):
            return self._migration_trigger

    def __init__(self, is_migrated: bool):
        # Todo: Freeze data
        self._is_migrated: bool = is_migrated

        self._tx_batch = self.BatchDict()
        self._icon_network_values: dict = {}    # It must be set by DB loading and network proposal

    @property
    def is_migrated(self) -> bool:
        return self._is_migrated

    def get_by_type(self, type_: 'IconNetworkValueType') -> Any:
        try:
            value = self._tx_batch.get(type_, self._icon_network_values[type_])
            if isinstance(value, Value):
                return value.value
        except KeyError:
            return None
        return None

    @property
    def service_config(self) -> int:
        return self.get_by_type(IconNetworkValueType.SERVICE_CONFIG)

    @property
    def step_price(self) -> int:
        return self.get_by_type(IconNetworkValueType.STEP_PRICE)

    @property
    def step_costs(self) -> Dict['StepType', int]:
        return self.get_by_type(IconNetworkValueType.STEP_COSTS)

    @property
    def max_step_limits(self) -> Dict['IconScoreContextType', int]:
        return self.get_by_type(IconNetworkValueType.MAX_STEP_LIMITS)

    @property
    def revision_code(self) -> int:
        return self.get_by_type(IconNetworkValueType.REVISION_CODE)

    @property
    def revision_name(self) -> str:
        return self.get_by_type(IconNetworkValueType.REVISION_NAME)

    @property
    def score_black_list(self) -> List['Address']:
        return self.get_by_type(IconNetworkValueType.SCORE_BLACK_LIST)

    @property
    def import_white_list(self) -> Dict[str, List[str]]:
        return self.get_by_type(IconNetworkValueType.IMPORT_WHITE_LIST)

    @property
    def irep(self) -> int:
        return self.get_by_type(IconNetworkValueType.IREP)

    def update_batch(self):
        for value in self._tx_batch.values():
            self._set(value)

    def clear_batch(self):
        self._tx_batch.clear()

    def migrate(self, data: List['Value']):
        """
        Migrates governance variable from SCORE DB to State DB.
        It will be called when updating governance score to version "".
        This method is called only once.
        :param data:
        :return:
        """
        if len(data) != IconNetworkValueType.gs_migration_count():
            raise InvalidParamsException("Migration data for Icon Network Values are insufficient")

        for value in data:
            self._tx_batch[value.TYPE] = value
        self._tx_batch.trigger_migration()

    def update_migration_if_succeed(self):
        if self._tx_batch.is_migration_triggered():
            self._is_migrated = True
            self.update_batch()

    def _set(self, value: 'Value'):
        self._icon_network_values[value.TYPE] = value

    def set_inv(self, value: 'Value', is_open: bool = False):
        """
        Set value on ICON Network Value from icon service.
        There are two cases of calling this method.
        First: Before migration
        Second: Initiating 'system value' when opening icon service (i.e. first initiation)
        Third:

        :param value:
        :param is_open:
        :return:
        """
        if not self._is_migrated or is_open is True:
            self._set(value)
        else:
            raise PermissionError(f"Invalid case of setting ICON Network value from icon-service"
                                  f"migration: {self._is_migrated} is open: {is_open}")

    def set_inv_to_tx_batch(self, value: 'Value'):
        """
        Set values on ICON Network Value and put these into DB.
        Only Governance SCORE can set values after migration.
        :param value:
        :return:
        """
        assert self._is_migrated
        # Update member variables
        # Check If value is valid
        self._tx_batch[value.TYPE] = value

    def copy(self) -> 'Container':
        """Copy container"""
        container = copy.copy(self)
        container._tx_batch = self.BatchDict()
        container._icon_network_values = copy.copy(self._icon_network_values)
        return container
