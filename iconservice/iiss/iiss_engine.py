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

from iconservice.iiss.iiss_msg_data import PRepUnregisterTx
from .iiss_data_creator import IissDataCreator
from .rc_data_storage import RcDataStorage
from .handler.stake_handler import StakeHandler
from .handler.delegation_handler import DelegationHandler
from .handler.iscore_handler import IScoreHandler
from .iiss_variable.iiss_variable import IissVariable
from .commit_delegator import CommitDelegator

from .reward_calc_proxy import RewardCalcProxy
from ..icon_constant import ConfigKey

if TYPE_CHECKING:
    from ..iconscore.icon_score_result import TransactionResult
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from ..precommit_data_manager import PrecommitData
    from ..database.db import ContextDatabase
    from iconcommons import IconConfig

    from ..base.address import Address
    from .iiss_msg_data import PRepRegisterTx, IissTxData


class IissEngine:
    icx_storage: 'IcxStorage' = None

    def __init__(self):
        self._invoke_handlers: dict = {
            'setStake': StakeHandler.handle_set_stake,
            'setDelegation': DelegationHandler.handle_set_delegation,
            'claimIScore': IScoreHandler.handle_claim_iscore
        }

        self._query_handler: dict = {
            'getStake': StakeHandler.handle_get_stake,
            'getDelegation': DelegationHandler.handle_get_delegation,
            'queryIScore': IScoreHandler.handle_query_iscore
        }

        self._reward_calc_proxy: 'RewardCalcProxy' = None
        self._rc_storage: 'RcDataStorage' = None
        self._variable: 'IissVariable' = None

    def open(self, context: 'IconScoreContext', conf: 'IconConfig', db: 'ContextDatabase'):
        self._reward_calc_proxy = RewardCalcProxy()

        self._rc_storage: 'RcDataStorage' = RcDataStorage()
        self._rc_storage.open(conf[ConfigKey.IISS_DB_ROOT_PATH])

        self._variable = IissVariable(db)
        self._variable.init_config(context, conf)

        self._init_commit_delegator()

        handlers: list = [StakeHandler, DelegationHandler, IScoreHandler]
        self._init_handlers(handlers)

    def _init_handlers(self, handlers: list):
        for handler in handlers:
            handler.icx_storage = self.icx_storage
            handler.reward_calc_proxy = self._reward_calc_proxy
            handler.rc_storage = self._rc_storage
            handler.variable = self._variable

    def _init_commit_delegator(self):
        CommitDelegator.icx_storage = self.icx_storage
        CommitDelegator.reward_calc_proxy = self._reward_calc_proxy
        CommitDelegator.rc_storage = self._rc_storage
        CommitDelegator.variable = self._variable

    def close(self):
        self._rc_storage.close()

    def invoke(self, context: 'IconScoreContext', data: dict, tx_result: 'TransactionResult') -> None:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params, tx_result)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def genesis_commit(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        CommitDelegator.genesis_update_db(context, precommit_data)
        self._rc_storage.commit(precommit_data.rc_block_batch)
        CommitDelegator.genesis_send_ipc(context, precommit_data)

    def commit(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        CommitDelegator.update_db(context, precommit_data)
        self._rc_storage.commit(precommit_data.rc_block_batch)
        CommitDelegator.send_ipc(context, precommit_data)

    def rollback(self):
        pass

    # TODO we don't allow inner function except these functions
    def put_reg_prep_candidate_for_rc_data(self,
                                           batch: list,
                                           address: 'Address',
                                           block_height: int):
        tx: 'PRepRegisterTx' = IissDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'IissTxData' = IissDataCreator.create_tx(address, block_height, tx)
        self._rc_storage.put(batch, iiss_tx_data)

    def put_unreg_prep_candidate_for_iiss_db(self,
                                             batch: list,
                                             address: 'Address',
                                             block_height: int):
        tx: 'PRepUnregisterTx' = IissDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'IissTxData' = IissDataCreator.create_tx(address, block_height, tx)
        self._rc_storage.put(batch, iiss_tx_data)

    def apply_candidate_delegated_offset_for_iiss_variable(self,
                                                           context: 'IconScoreContext',
                                                           offset: int):
        total_delegated_amount: int = self._variable.issue.get_total_candidate_delegated(context)
        self._variable.issue.put_total_candidate_delegated(context,
                                                           total_delegated_amount + offset)
