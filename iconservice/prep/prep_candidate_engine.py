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

from ..icon_constant import PREP_MAX_PREPS
from ..database.db import ContextDatabase
from ..base.address import Address
from ..icx.icx_storage import Intent
from ..iconscore.icon_score_result import TransactionResult

from .prep_candidate_info_for_sort import PRepCandidateInfoForSort
from .prep_candidate_container import PRepCandiateInfoMapper, PRepCandidateSortedInfos
from .prep_candidate import PRepCandidate
from .prep_candidate_storage import PRepCandidateStorage
from .prep_variable.prep_variable import PRepVariable
from .handler.prep_candidate_handler import PRepCandidateHandler
from .prep_candidate_batch import BatchSlotType, RegPRep, UpdatePRep, UnregPRep
from .prep_candidate_utils import PRepCandidateUtils
from .prep_variable.prep_variable_storage import PReps

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from ..icx.icx_account import Account
    from .prep_candidate_batch import PRepCandidateBatch
    from .prep_variable.prep_variable_storage import GovernanceVariable
    from .prep_variable.prep_variable_storage import PRep
    from iconcommons import IconConfig


class PRepCandidateEngine(object):
    icx_storage: 'IcxStorage' = None

    def __init__(self) -> None:
        self._invoke_handlers: dict = {
            'registerPRepCandidate': PRepCandidateHandler.handle_reg_prep_candidate,
            'unregisterPRepCandidate': PRepCandidateHandler.handle_unreg_prep_candidate,
            'setPRepCandidate': PRepCandidateHandler.handle_set_prep_candidate
        }

        self._query_handler: dict = {
            'getPRepCandidate': PRepCandidateHandler.handle_get_prep_candidate,
            'getPRepCandidateDelegationInfo': PRepCandidateHandler.handle_get_prep_candidate_delegation_info,
            'getPRepList': PRepCandidateHandler.handle_get_prep_list,
            'getPRepCandidateList': PRepCandidateHandler.handle_get_prep_candidate_list
        }

        self._storage: 'PRepCandidateStorage' = None
        self._variable: 'PRepVariable' = None
        self._candidate_info_mapper: 'PRepCandiateInfoMapper' = None
        self._candidate_sorted_infos: 'PRepCandidateSortedInfos' = None

    def open(self, context: 'IconScoreContext', conf: 'IconConfig', db: 'ContextDatabase') -> None:
        self._storage = PRepCandidateStorage(db)

        self._variable = PRepVariable(db)
        self._variable.init_config(context, conf)

        self._candidate_info_mapper: 'PRepCandiateInfoMapper' = PRepCandiateInfoMapper()
        self._candidate_sorted_infos: 'PRepCandidateSortedInfos' = PRepCandidateSortedInfos()

        handlers: list = [PRepCandidateHandler]
        self._init_handlers(handlers)

    def _init_handlers(self, handlers: list):
        for handler in handlers:
            handler.icx_storage = self.icx_storage
            handler.prep_storage = self._storage
            handler.prep_variable = self._variable
            handler.prep_candidates = self._candidate_sorted_infos

    def load_prep_candidates(self, context: 'IconScoreContext', icx_storage: 'IcxStorage'):
        for key, value in self._storage.get_prep_candiates():
            address: 'Address' = Address.from_bytes(key)
            account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATION)
            self._add_prep_candidate_objects(address, value, account.delegated_amount)
        sorted_objs: list = self._candidate_info_mapper.to_genesis_sorted_list()
        self._candidate_sorted_infos.genesis_update(sorted_objs)

    def _add_prep_candidate_objects(self, address: 'Address', value: bytes, total_delegated: int):
        candidate: 'PRepCandidate' = PRepCandidate.from_bytes(value, address)
        obj: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort.create_object(address,
                                                                                 candidate.name,
                                                                                 candidate.block_height,
                                                                                 candidate.tx_index)
        obj.update(total_delegated)
        self._candidate_info_mapper[address] = obj

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

    def commit(self, prep_candiate_block_batch: 'PRepCandidateBatch'):
        # TODO calc Batch
        self._update_prep_candidates(prep_candiate_block_batch)
        # state DB write DB

    def _update_prep_candidates(self, prep_candiate_block_batch: 'PRepCandidateBatch'):
        for address, batch in prep_candiate_block_batch.items():
            put_obj = batch.get(BatchSlotType.PUT)
            if put_obj:
                if isinstance(put_obj, RegPRep):
                    info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort.create_object(address,
                                                                                              put_obj.name,
                                                                                              put_obj.block_height,
                                                                                              put_obj.tx_index)
                    self._candidate_info_mapper[address] = info
                    self._candidate_sorted_infos.add_info(info)
                elif isinstance(put_obj, UnregPRep):
                    del self._candidate_info_mapper[address]
                    self._candidate_sorted_infos.del_info(address)

            update_obj = batch.get(BatchSlotType.UPDATE)
            if update_obj:
                if isinstance(update_obj, UpdatePRep):
                    obj: 'PRepCandidateInfoForSort' = self._candidate_info_mapper[address]
                    obj.update(update_obj.total_delegated)
                    self._candidate_sorted_infos.update_info(address, update_obj.total_delegated)

    def rollback(self):
        pass

    # TODO we don't allow inner function except these functions
    @classmethod
    def update_prep_candidate_info_for_sort(cls,
                                            context: 'IconScoreContext',
                                            address: 'Address',
                                            total_delegated: int):
        PRepCandidateUtils.update_prep_candidate_info_for_sort(context, address, total_delegated)

    def is_candidate(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return self._storage.is_candidate(context, address)

    def get_gv(self, context: 'IconScoreContext') -> 'GovernanceVariable':
        return self._variable.get_gv(context)

    def get_preps(self, context: 'IconScoreContext') -> List['PRep']:
        return self._variable.get_preps(context)

    def update_preps(self, context: 'IconScoreContext'):
        candidates: list = self._candidate_sorted_infos.get()
        preps: list = candidates[:PREP_MAX_PREPS]
        self._variable.put_preps(context, PReps.from_list(preps))
