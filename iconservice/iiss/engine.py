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

from iconcommons.logger import Logger
from .reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from iconservice.iiss.reward_calc.ipc.message import CalculateResponse
from .commit_delegator import CommitDelegator
from .handler.delegation_handler import DelegationHandler
from .handler.iscore_handler import IScoreHandler
from .handler.stake_handler import StakeHandler
from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .reward_calc.msg_data import PRepUnregisterTx
from ..icon_constant import IISS_SOCKET_PATH
from ..iiss.issue_formula import IssueFormula

if TYPE_CHECKING:
    from ..iconscore.icon_score_result import TransactionResult
    from ..iconscore.icon_score_context import IconScoreContext
    from ..precommit_data_manager import PrecommitData

    from ..base.address import Address
    from .reward_calc.msg_data import PRepRegisterTx, TxData


class Engine:

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
        self._formula: 'IssueFormula' = None

    def open(self, context: 'IconScoreContext', path: str):
        self._init_reward_calc_proxy(path)

        self._init_commit_delegator()
        # todo: consider formula managing r min, r max, r point
        self._formula = IssueFormula()

        handlers: list = [StakeHandler, DelegationHandler, IScoreHandler]
        self._init_handlers(handlers)

    # TODO implement calculate callback function
    def calculate_callback(self, cb_data: 'CalculateResponse'):
        Logger.debug(tag="iiss", msg=f"calculate callback called with {cb_data}")

    def _init_reward_calc_proxy(self, data_path: str):
        self._reward_calc_proxy = RewardCalcProxy(calc_callback=self.calculate_callback)
        self._reward_calc_proxy.open(sock_path=IISS_SOCKET_PATH, iiss_db_path=data_path)
        self._reward_calc_proxy.start()

    def _close_reward_calc_proxy(self):
        self._reward_calc_proxy.stop()
        self._reward_calc_proxy.close()

    def _init_handlers(self, handlers: list):
        for handler in handlers:
            handler.reward_calc_proxy = self._reward_calc_proxy

    def _init_commit_delegator(self):
        CommitDelegator.reward_calc_proxy = self._reward_calc_proxy

    def close(self):
        self._close_reward_calc_proxy()

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
        context.storage.iiss.commit(precommit_data.rc_block_batch)
        CommitDelegator.genesis_send_ipc(context, precommit_data)

    def commit(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        CommitDelegator.update_db(context, precommit_data)
        context.storage.iiss.commit(precommit_data.rc_block_batch)
        CommitDelegator.send_ipc(context, precommit_data)

    def create_icx_issue_info(self, context: 'IconScoreContext'):
        gv: 'GovernanceVariable' = context.storage.prep.get_gv(context)

        iiss_data_for_issue = {
            "prep": {
                "incentive": gv.incentive_rep,
                "rewardRate": context.storage.iiss.get_reward_prep(context).reward_rate,
                "totalDelegation": context.storage.iiss.get_total_candidate_delegated(context)
            }
        }
        for group in iiss_data_for_issue:
            issue_amount_per_group = self._formula.calculate(group, iiss_data_for_issue[group])
            iiss_data_for_issue[group]["value"] = issue_amount_per_group

        return iiss_data_for_issue

    def rollback(self):
        pass

    # TODO we don't allow inner function except these functions
    def put_reg_prep_candidate_for_rc_data(self,
                                           batch: list,
                                           address: 'Address',
                                           block_height: int):
        tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        self._rc_storage.storage.rc.put(batch, iiss_tx_data)

    def put_unreg_prep_candidate_for_iiss_db(self,
                                             batch: list,
                                             address: 'Address',
                                             block_height: int):
        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        self._rc_storage.put(batch, iiss_tx_data)

    def apply_candidate_delegated_offset_for_iiss_variable(self,
                                                           context: 'IconScoreContext',
                                                           offset: int):
        total_delegated_amount: int = self._variable.issue.get_total_candidate_delegated(context)
        self._variable.issue.put_total_candidate_delegated(context,
                                                           total_delegated_amount + offset)
