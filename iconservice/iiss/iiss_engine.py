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

from typing import TYPE_CHECKING, Any

from .rc_data_storage import RcDataStorage
from .reward_calc_proxy import RewardCalcProxy
from ..icon_constant import ConfigKey

if TYPE_CHECKING:
    from ..iconscore.icon_score_result import TransactionResult
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from iconcommons import IconConfig


class IissGlobalVariable:
    def __init__(self):
        self.gv: dict = {}
        self.unstake_lock_period: int = 0
        self.prep_list: dict = {}
        self.calc_period: int = 0


class IissEngine:
    icx_storage: 'IcxStorage' = None

    def __init__(self):
        self._invoke_handlers: dict = {
        }

        self._query_handler: dict = {
        }

        self._data_storage: 'RcDataStorage' = None
        self._reward_calc_proxy: 'RewardCalcProxy' = None

        self._global_variable: 'IissGlobalVariable' = None

    def open(self, conf: 'IconConfig'):
        self._reward_calc_proxy = RewardCalcProxy()
        self._data_storage: 'RcDataStorage' = RcDataStorage()
        self._data_storage.open(conf[ConfigKey.IISS_DB_ROOT_PATH])

    def close(self):
        self._data_storage.close()

    def invoke(self, context: 'IconScoreContext',
               data: dict,
               tx_result: 'TransactionResult') -> None:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params, tx_result)

    def query(self, context: 'IconScoreContext',
              data: dict) -> Any:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def commit(self, block_hash: bytes):
        # todo: should get procommit data
        # TODO RC
        pass

    def rollback(self, block_hash: bytes):
        pass
