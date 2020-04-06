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


from typing import Optional, TYPE_CHECKING, List

from .container import Container
from .data.value import Value, VALUE_MAPPER
from ..base.ComponentBase import StorageBase
from ..database.db import ContextDatabase
from ..icon_constant import IconNetworkValueType
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    MIGRATION_FLAG: bytes = b'mf'

    def __init__(self, db: 'ContextDatabase'):
        super().__init__(db)

    def get_container(self, context: 'IconScoreContext') -> Optional['Container']:
        """
        Load container from DB after migration

        :param context:
        :return: Return'None' if migration has not been finished
        """
        is_migrated: bool = self._get_migration_flag(context)
        container: Optional['Container'] = None
        if not is_migrated:
            return container

        container: 'Container' = Container(is_migrated)
        for type_ in IconNetworkValueType:
            value: Optional['Value'] = self._get_value(context, type_)
            if value is not None:
                container.set_inv(value, is_open=True)
        return container

    def migrate(self, context: 'IconScoreContext', data: List['Value']):
        for value in data:
            self.put_value(context, value)
        self._db.put(context, self.MIGRATION_FLAG, MsgPackForDB.dumps(True))

    def _get_migration_flag(self, context: 'IconScoreContext') -> bool:
        return bool(self._db.get(context, self.MIGRATION_FLAG))

    def put_value(self, context: 'IconScoreContext', value: 'Value'):
        self._db.put(context, value.make_key(), value.to_bytes())

    def _get_value(self, context: 'IconScoreContext', type_: 'IconNetworkValueType') -> Optional['Value']:
        assert isinstance(type_, IconNetworkValueType)
        value: Optional[bytes] = self._db.get(context, Value.PREFIX + type_.value)
        if value is None:
            return None

        value: 'value' = VALUE_MAPPER[type_].from_bytes(value)
        return value
