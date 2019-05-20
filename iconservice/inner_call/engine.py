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

from typing import Optional, TYPE_CHECKING

from ..base.exception import MethodNotFoundException
from ..iconscore.icon_score_context import IconScoreContext
from ..prep.handler.candidate_handler import CandidateHandler

if TYPE_CHECKING:
    from ..prep.candidate import Candidate


class Engine(object):
    def __init__(self):
        self._handler = {
            "ise_getPReps": self._handle_get_preps
        }

    def query(self, context: 'IconScoreContext', request: dict) -> dict:
        method: str = request["method"]
        params: Optional[dict] = request.get("params")

        if method not in self._handler:
            raise MethodNotFoundException(f"Method not found: {method}")

        return self._handler[method](context, params)

    @staticmethod
    def _handle_get_preps(context: 'IconScoreContext', params: dict) -> dict:
        prep_list = context.prep_candidate_engine.get_preps(context)
        prep_result = []
        for prep in prep_list:
            candidate: 'Candidate' = CandidateHandler.prep_storage.get_candidate(context, prep.address)
            data = {
                "id": str(candidate.address),
                "publicKey": candidate.public_key,
                "url": candidate.url
            }
            prep_result.append(data)

        return {
            "result": {
                "blockHeight": context.block.height,
                "preps": prep_result
            }
        }
