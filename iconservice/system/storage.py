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


from typing import Any, Optional, TYPE_CHECKING, List

from .data.system_data import SystemData, SYSTEM_DATA_MAPPER
from .value import SystemValue
from ..base.ComponentBase import StorageBase
from ..database.db import ContextDatabase
from ..icon_constant import SystemValueType
from ..utils.msgpack_for_db import MsgPackForDB


if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    MIGRATION_FLAG: bytes = b'mf'

    def __init__(self, db: 'ContextDatabase'):
        super().__init__(db)

    def get_system_value(self, context: 'IconScoreContext') -> Optional['SystemValue']:
        """
        Load system value from DB after migration

        :param context:
        :return: Return'None' if migration has not been finished
        """
        is_migrated: bool = self._get_migration_flag(context)
        system_value: Optional['SystemValue'] = None
        if not is_migrated:
            return system_value

        system_value: 'SystemValue' = SystemValue(is_migrated)
        for type_ in SystemValueType:
            system_data: 'SystemData' = self._get_value(context, type_)
            if system_data is not None:
                system_value.set_by_icon_service(system_data, is_open=True)
        return system_value

    def put_migration_flag(self, context: 'IconScoreContext'):
        self._db.put(context, self.PREFIX + self.MIGRATION_FLAG, MsgPackForDB.dumps(True))

    def _get_migration_flag(self, context: 'IconScoreContext') -> bool:
        return bool(self._db.get(context, self.PREFIX + self.MIGRATION_FLAG))

    def put_value(self, context: 'IconScoreContext', system_value: 'SystemData'):
        self._db.put(context, system_value.make_key(), system_value.to_bytes())

    def _get_value(self, context: 'IconScoreContext', type_: 'SystemValueType') -> 'SystemData':
        assert isinstance(type_, SystemValueType)
        value: Optional[bytes] = self._db.get(context, SystemData.PREFIX + type_.value)
        if value is None:
            return None

        system_data: 'SystemData' = SYSTEM_DATA_MAPPER[type_].from_bytes(value)
        return system_data
