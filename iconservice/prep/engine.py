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

from typing import TYPE_CHECKING, Any, Optional

from iconcommons.logger import Logger
from .candidate_container import CandidateContainer
from .handler.candidate_handler import CandidateHandler
from .term import Term
from ..base.address import Address
from ..iconscore.icon_score_result import TransactionResult

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Engine(object):

    def __init__(self) -> None:
        Logger.debug("PRepEngine.__init__() start")

        self._invoke_handlers: dict = {
            'registerPRepCandidate': CandidateHandler.handle_reg_prep_candidate,
            # 'unregisterPRepCandidate': CandidateHandler.handle_unreg_prep_candidate,
            # 'setPRepCandidate': CandidateHandler.handle_set_prep_candidate
        }

        self._query_handler: dict = {
            'getPRepCandidate': CandidateHandler.handle_get_prep_candidate,
            # 'getPRepCandidateDelegationInfo': CandidateHandler.handle_get_prep_candidate_delegation_info,
            # 'getPRepList': CandidateHandler.handle_get_prep_list,
            # 'getPRepCandidateList': CandidateHandler.handle_get_prep_candidate_list
        }

        self.candidates: Optional['CandidateContainer'] = None
        self.term = Term()

        Logger.debug("PRepEngine.__init__() end")

    def open(self, context: 'IconScoreContext') -> None:
        self._init_handlers()

        self.candidates = CandidateContainer()
        self.candidates.load(context)

        self.term.load(context)

    def _init_handlers(self):
        for handler in (CandidateHandler,):
            handler.prep_candidates = self.candidates

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
        pass

    def commit(self, context: 'IconScoreContext'):
        """If the current P-Rep term is over, update term with new information
        which has P-Rep list(address, delegated amount), start height, end height, incentive_rep

        :param context:
        :return:
        """
        pass

    def rollback(self):
        pass

    def is_candidate(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return address in self.candidates
