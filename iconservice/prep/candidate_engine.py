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

from typing import TYPE_CHECKING, Any, List

from .candidate import Candidate
from .candidate_batch import RegPRep, UpdatePRep, UnregPRep
from .candidate_container import CandidateInfoMapper, SortedCandidates
from .candidate_storage import CandidateStorage
from .candidate_utils import CandidateUtils
from .handler.candidate_handler import CandidateHandler
from .variable.variable import Variable
from .variable.variable_storage import PReps
from ..base.address import Address
from ..database.db import ContextDatabase
from ..icon_constant import PREP_MAX_PREPS
from ..iconscore.icon_score_result import TransactionResult
from ..icx.icx_storage import Intent

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from ..icx.icx_account import Account
    from .candidate_batch import CandidateBatch
    from .variable.variable_storage import GovernanceVariable
    from .variable.variable_storage import PRep
    from iconcommons import IconConfig


class CandidateEngine(object):
    icx_storage: 'IcxStorage' = None

    def __init__(self) -> None:
        self._invoke_handlers: dict = {
            'registerPRepCandidate': CandidateHandler.handle_reg_prep_candidate,
            'unregisterPRepCandidate': CandidateHandler.handle_unreg_prep_candidate,
            'setPRepCandidate': CandidateHandler.handle_set_prep_candidate
        }

        self._query_handler: dict = {
            'getPRepCandidate': CandidateHandler.handle_get_prep_candidate,
            'getPRepCandidateDelegationInfo': CandidateHandler.handle_get_prep_candidate_delegation_info,
            'getPRepList': CandidateHandler.handle_get_prep_list,
            'getPRepCandidateList': CandidateHandler.handle_get_prep_candidate_list
        }

        self._storage: 'CandidateStorage' = None
        self._variable: 'Variable' = None
        self._candidate_info_mapper: 'CandidateInfoMapper' = None
        self._candidate_sorted_infos: 'SortedCandidates' = None

    def open(self, context: 'IconScoreContext', conf: 'IconConfig', db: 'ContextDatabase') -> None:
        self._storage = CandidateStorage(db)

        self._variable = Variable(db)
        self._variable.init_config(context, conf)

        self._candidate_info_mapper: 'CandidateInfoMapper' = CandidateInfoMapper()
        self._candidate_sorted_infos: 'SortedCandidates' = SortedCandidates()

        handlers: list = [CandidateHandler]
        self._init_handlers(handlers)

    def _init_handlers(self, handlers: list):
        for handler in handlers:
            handler.icx_storage = self.icx_storage
            handler.prep_storage = self._storage
            handler.prep_variable = self._variable
            handler.prep_candidates = self._candidate_sorted_infos

    def load_prep_candidates(self, context: 'IconScoreContext', icx_storage: 'IcxStorage'):
        for key, value in self._storage.get_prep_candidates():
            address: 'Address' = Address.from_bytes_including_prefix(key)
            account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)
            self._add_prep_candidates(address, value, account.delegated_amount)
        sorted_objs: list = self._candidate_info_mapper.to_genesis_sorted_list()
        self._candidate_sorted_infos.genesis_update(sorted_objs)
        self._update_preps(context)

    def _add_prep_candidates(self, address: 'Address', value: bytes, delegated: int):
        candidate: 'Candidate' = Candidate.from_bytes(address, value)
        candidate.delegated = delegated
        self._candidate_info_mapper[address] = candidate

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

    def close(self):
        if self._storage:
            self._storage.close()
            self._storage = None

    def commit(self, context: 'IconScoreContext', prep_candiate_block_batch: 'CandidateBatch'):
        # TODO calc Batch
        self._commit_candidates(context, prep_candiate_block_batch)
        # state DB write DB

    def _commit_candidates(self, context: 'IconScoreContext', prep_candiate_block_batch: 'CandidateBatch'):
        dirty: bool = False

        preps_address: list = []
        preps = self._variable.get_preps(context)
        for prep in preps:
            preps_address.append(prep.address)

        for address, batch in prep_candiate_block_batch.items():
            for obj in batch.values():
                if isinstance(obj, RegPRep):
                    candidate: 'Candidate' = self._storage.get_candidate(context, address)
                    self._candidate_info_mapper[address] = candidate
                    self._candidate_sorted_infos.add_candidate(candidate)
                elif isinstance(obj, UnregPRep):
                    del self._candidate_info_mapper[address]
                    self._candidate_sorted_infos.del_candidate(address)
                elif isinstance(obj, UpdatePRep):
                    candidate: 'Candidate' = self._candidate_info_mapper[address]
                    candidate.delegated = obj.delegated
                    self._candidate_sorted_infos.update_candidate(address, obj.delegated)
                    if candidate.address in preps_address:
                        dirty: bool = True
                else:
                    pass

        if dirty:
            self._update_preps(context)

    def rollback(self):
        pass

    def _update_preps(self, context: 'IconScoreContext'):
        preps: list = []

        for prep in self._variable.get_preps(context):
            info: 'Candidate' = self._candidate_info_mapper[prep.address]
            preps.append(info)

        context.updated_preps: List['PRep'] = PReps.from_list(preps).preps

    # TODO we don't allow inner function except these functions
    @classmethod
    def update_sorted_candidates(cls,
                                 context: 'IconScoreContext',
                                 address: 'Address',
                                 delegated: int):
        CandidateUtils.update_candidate(context, address, delegated)

    def is_candidate(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return self._storage.is_candidate(context, address)

    def get_gv(self, context: 'IconScoreContext') -> 'GovernanceVariable':
        return self._variable.get_gv(context)

    def get_preps(self, context: 'IconScoreContext') -> List['PRep']:
        return self._variable.get_preps(context)

    def update_preps_to_variable(self, context: 'IconScoreContext'):
        # only change prep term call
        candidates: list = self._candidate_sorted_infos.to_list()
        preps: list = candidates[:PREP_MAX_PREPS]
        self._variable.put_preps(context, PReps.from_list(preps))
        self._update_preps(context)

