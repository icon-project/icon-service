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

from typing import TYPE_CHECKING

from .candidate_batch import BatchSlotType, RegPRep, UpdatePRep, UnregPRep

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address


class CandidateUtils:
    @classmethod
    def register_candidate(cls,
                           context: 'IconScoreContext',
                           address: 'Address',
                           delegated: int):
        data: dict = \
            {
                BatchSlotType.PUT_DEL: RegPRep(),
                BatchSlotType.UPDATE: UpdatePRep(delegated)
            }
        cls._add_batch_item(context, address, data)

    @classmethod
    def update_candidate(cls,
                         context: 'IconScoreContext',
                         address: 'Address',
                         delegated: int):
        data: dict = \
            {
                BatchSlotType.UPDATE: UpdatePRep(delegated)
            }
        cls._add_batch_item(context, address, data)

    @classmethod
    def unregister_candidate(cls,
                             context: 'IconScoreContext',
                             address: 'Address'):
        data: dict = \
            {
                BatchSlotType.PUT_DEL: UnregPRep()
            }
        cls._add_batch_item(context, address, data)

    @classmethod
    def _add_batch_item(cls,
                        context: 'IconScoreContext',
                        address: 'Address',
                        items: dict):
        if address not in context.prep_candidate_tx_batch:
            context.prep_candidate_tx_batch[address] = items
        else:
            prev: dict = context.prep_candidate_tx_batch[address]
            prev.update(items)

    @staticmethod
    def compare_key(x, y) -> int:
        if x < y:
            return 1
        elif x > y:
            return -1
        else:
            return 0
