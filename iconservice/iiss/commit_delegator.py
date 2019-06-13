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

from typing import TYPE_CHECKING, List, Optional

from iconcommons import Logger

from .issue_formula import IssueFormula
from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .variable.issue_storage import Reward
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from ..precommit_data_manager import PrecommitData
    from ..base.address import Address
    from ..prep.variable.variable_storage import GovernanceVariable, PRep
    from .ipc.reward_calc_proxy import RewardCalcProxy
    from .reward_calc.data_storage import DataStorage as RewardCalcDataStorage
    from .reward_calc.msg_data import Header, BlockProduceInfoData, PRepsData, GovernanceVariable
    from .variable.variable import Variable


class CommitDelegator(object):
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RewardCalcDataStorage' = None
    variable: 'Variable' = None

    @classmethod
    def genesis_update_db(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        context.prep_engine.update_preps_to_variable(context)
        cls._put_next_calc_block_height(context, precommit_data.block.height)

        cls._put_header_for_rc(context, precommit_data)
        cls._put_gv_for_rc(context, precommit_data)
        cls._put_preps_for_rc(context, precommit_data)

    @classmethod
    def genesis_send_ipc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        block_height: int = precommit_data.block.height
        path: str = cls.rc_storage.create_db_for_calc(precommit_data.block.height)
        cls.reward_calc_proxy.commit_block(True, block_height, precommit_data.block.hash)
        cls.reward_calc_proxy.calculate(path, block_height)

    @classmethod
    def update_db(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):

        # every block time
        cls._put_block_produce_info_for_rc(context, precommit_data)
        # cls._put_preps_for_rc(context, precommit_data)

        if not cls._check_update_calc_period(context, precommit_data):
            return

        cls._put_header_for_rc(context, precommit_data)
        cls._put_gv_for_rc(context, precommit_data)

    @classmethod
    def send_ipc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        # TODO: Disable reward_calc_proxy for test
        return

        # every block
        cls.reward_calc_proxy.commit_block(True, precommit_data.block.height, precommit_data.block.hash)

        if not cls._check_update_calc_period(context, precommit_data):
            return

        block_height: int = precommit_data.block.height
        path: str = cls.rc_storage.create_db_for_calc(precommit_data.block.height)
        cls.reward_calc_proxy.calculate(path, block_height)
        cls._put_next_calc_block_height(context, precommit_data.block.height)

    @classmethod
    def _check_update_calc_period(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData') -> bool:
        block_height: int = precommit_data.block.height
        check_next_block_height: Optional[int] = cls.variable.issue.get_calc_next_block_height(context)
        if check_next_block_height is None:
            return False

        return block_height == check_next_block_height

    @classmethod
    def _put_next_calc_block_height(cls, context: 'IconScoreContext', block_height: int):
        calc_period: int = cls.variable.issue.get_calc_period(context)
        if calc_period is None:
            raise InvalidParamsException("Fail put next calc block height: didn't init yet")
        cls.variable.issue.put_calc_next_block_height(context, block_height + calc_period)

    @classmethod
    def _put_header_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        data: 'Header' = RewardCalcDataCreator.create_header(0, precommit_data.block.height)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_gv_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        gv: 'GovernanceVariable' = context.prep_engine.get_gv(context)

        current_total_supply = cls.icx_storage.get_total_supply(context)
        current_total_candidate_delegated = cls.variable.issue.get_total_candidate_delegated(context)
        reward_prep: 'Reward' = cls.variable.issue.get_reward_prep(context)

        reward_rep: int = IssueFormula.calculate_r_rep(reward_prep.reward_min,
                                                       reward_prep.reward_max,
                                                       reward_prep.reward_point,
                                                       current_total_supply,
                                                       current_total_candidate_delegated)
        calculated_incentive_rep: int = IssueFormula.calculate_i_rep_per_block_contributor(gv.incentive_rep)
        reward_prep.reward_rate = reward_rep
        cls.variable.issue.put_reward_prep(context, reward_prep)

        data: 'GovernanceVariable' = RewardCalcDataCreator.create_gv_variable(precommit_data.block.height,
                                                                              calculated_incentive_rep,
                                                                              reward_rep)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_block_produce_info_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        if precommit_data.prev_block_generator is None or precommit_data.prev_block_validators is None:
            return
        
        generator: 'Address' = precommit_data.prev_block_generator
        validators: List['Address'] = precommit_data.prev_block_validators

        Logger.debug(f"put_block_produce_info_for_rc", "iiss")
        data: 'BlockProduceInfoData' = RewardCalcDataCreator.create_block_produce_info_data(precommit_data.block.height,
                                                                                            generator,
                                                                                            validators)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_preps_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        preps: List['PRep'] = context.updated_preps

        if len(preps) == 0:
            return

        total_candidate_delegated: int = 0
        for prep in preps:
            total_candidate_delegated += prep.delegated

        Logger.debug(f"put_preps_for_rc: total_candidate_delegated{total_candidate_delegated}", "iiss")

        data: 'PRepsData' = RewardCalcDataCreator.create_prep_data(precommit_data.block.height,
                                                                   total_candidate_delegated,
                                                                   preps)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)
