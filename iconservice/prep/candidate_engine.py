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
from .candidate_batch import BatchSlotType, RegPRep, UpdatePRep, UnregPRep
from .candidate_container import CandidateInfoMapper, CandidateSortedInfos
from .candidate_info_for_sort import CandidateInfoForSort
from .candidate_storage import CandidateStorage
from .candidate_utils import CandidateUtils
from .handler.candidate_handler import CandidateHandler
from .variable.variable import Variable
from .variable.variable_storage import PReps
from ..base.address import Address
from ..database.db import ContextDatabase
from ..icon_constant import PREP_MAX_PREPS, ConfigKey
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
        self._candidate_sorted_infos: 'CandidateSortedInfos' = None

        self._prep_infos_dirty_include_sub_prep: bool = False
        self._builtin_owner: Address = None

        # read only
        self._prep_mapper_include_sub_prep: dict = None
        self._prep_infos_include_sub_prep: 'CandidateSortedInfos' = None

    def open(self, context: 'IconScoreContext', conf: 'IconConfig', db: 'ContextDatabase') -> None:
        self._storage = CandidateStorage(db)

        self._variable = Variable(db)
        self._variable.init_config(context, conf)

        self._candidate_info_mapper: 'CandidateInfoMapper' = CandidateInfoMapper()
        self._candidate_sorted_infos: 'CandidateSortedInfos' = CandidateSortedInfos()

        self._prep_mapper_include_sub_prep: dict = {}
        self._prep_infos_include_sub_prep: 'CandidateSortedInfos' = CandidateSortedInfos()

        handlers: list = [CandidateHandler]
        self._init_handlers(handlers)
        self._builtin_owner = Address.from_string(conf[ConfigKey.BUILTIN_SCORE_OWNER])

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
            self._add_prep_candidate_objects(address, value, account.delegated_amount)
        sorted_objs: list = self._candidate_info_mapper.to_genesis_sorted_list()
        self._candidate_sorted_infos.genesis_update(sorted_objs)
        self._update_prep_infos_include_sub_prep(context)

    def _add_prep_candidate_objects(self, address: 'Address', value: bytes, total_delegated: int):
        candidate: 'Candidate' = Candidate.from_bytes(value, address)
        obj: 'CandidateInfoForSort' = CandidateInfoForSort.create_object(address,
                                                                         candidate.name,
                                                                         candidate.block_height,
                                                                         candidate.tx_index)
        obj.update(total_delegated)
        self._candidate_info_mapper[address] = obj

    def invoke(self, context: 'IconScoreContext', data: dict, tx_result: 'TransactionResult') -> None:
        method: str = data['method']
        params: dict = data.get('params', {})

        handler: callable = self._invoke_handlers[method]
        handler(context, params, tx_result)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data.get('params', {})

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def close(self):
        if self._storage:
            self._storage.close()
            self._storage = None

    def commit(self, prep_candiate_block_batch: 'CandidateBatch'):
        # TODO calc Batch
        self._update_prep_candidates(prep_candiate_block_batch)
        # state DB write DB

    def _update_prep_candidates(self, prep_candiate_block_batch: 'CandidateBatch'):
        self._prep_infos_dirty_include_sub_prep = False

        for address, batch in prep_candiate_block_batch.items():
            put_obj = batch.get(BatchSlotType.PUT)
            if put_obj:
                if isinstance(put_obj, RegPRep):
                    info: 'CandidateInfoForSort' = CandidateInfoForSort.create_object(address,
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
                    obj: 'CandidateInfoForSort' = self._candidate_info_mapper[address]
                    obj.update(update_obj.total_delegated)
                    self._candidate_sorted_infos.update_info(address, update_obj.total_delegated)
                    if obj.address in self._prep_mapper_include_sub_prep:
                        self._prep_infos_dirty_include_sub_prep = True

    def rollback(self):
        pass

    # TODO we don't allow inner function except these functions
    @classmethod
    def update_prep_candidate_info_for_sort(cls,
                                            context: 'IconScoreContext',
                                            address: 'Address',
                                            total_delegated: int):
        CandidateUtils.update_prep_candidate_info_for_sort(context, address, total_delegated)

    def is_candidate(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return self._storage.is_candidate(context, address)

    def get_gv(self, context: 'IconScoreContext') -> 'GovernanceVariable':
        return self._variable.get_gv(context)

    def get_preps(self, context: 'IconScoreContext') -> List['PRep']:
        return self._variable.get_preps(context)

    def get_preps_include_sub_prep(self) -> list:
        prep_infos: list = self._prep_infos_include_sub_prep.to_list()
        return PReps.from_list(prep_infos).preps

    def update_preps_from_variable(self, context: 'IconScoreContext'):
        candidates: list = self._candidate_sorted_infos.to_list()
        preps: list = candidates[:PREP_MAX_PREPS]
        self._variable.put_preps(context, PReps.from_list(preps))
        self._update_prep_infos_include_sub_prep(context)

    def _update_prep_infos_include_sub_prep(self, context: 'IconScoreContext'):
        self._prep_infos_include_sub_prep.clear()

        table: dict = self._candidate_sorted_infos.to_dict()

        for prep in self._variable.get_preps(context):
            info: 'CandidateInfoForSort' = table[prep.address]
            self._prep_infos_include_sub_prep.add_info(info)

        self._prep_infos_dirty_include_sub_prep: bool = True
        self._prep_mapper_include_sub_prep: dict = table

    @property
    def prep_infos_dirty_include_sub_prep(self) -> bool:
        return self._prep_infos_dirty_include_sub_prep
