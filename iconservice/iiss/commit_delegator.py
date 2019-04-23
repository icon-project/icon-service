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
from .iiss_data_creator import IissDataCreator
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage
    from ..precommit_data_manager import PrecommitData
    from ..base.address import Address
    from ..prep.prep_variable.prep_variable_storage import GovernanceVariable, PRep
    from .ipc.reward_calc_proxy import RewardCalcProxy
    from .rc_data_storage import RcDataStorage
    from .iiss_msg_data import IissHeader, IissBlockProduceInfoData, PrepsData, IissGovernanceVariable
    from .iiss_variable.iiss_variable import IissVariable


class CommitDelegator(object):
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RcDataStorage' = None
    variable: 'IissVariable' = None

    @classmethod
    def genesis_update_db(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        context.prep_candidate_engine.update_preps_from_variable(context)
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
        cls._put_preps_for_rc(context, precommit_data)

        if not cls._check_update_calc_period(context, precommit_data):
            return

        cls._put_header_for_rc(context, precommit_data)
        cls._put_gv_for_rc(context, precommit_data)

    @classmethod
    def send_ipc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
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
        data: 'IissHeader' = IissDataCreator.create_header(0, precommit_data.block.height)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_gv_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        gv: 'GovernanceVariable' = context.prep_candidate_engine.get_gv(context)

        # TODO calc variable
        reward_rep: int = cls.variable.issue.get_reward_rep(context)
        calculated_incentive_rep: int = gv.incentive_rep

        data: 'IissGovernanceVariable' = IissDataCreator.create_gv_variable(precommit_data.block.height,
                                                                            calculated_incentive_rep,
                                                                            reward_rep)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_block_produce_info_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        if precommit_data.prev_block_contributors is None:
            return
        
        generator: 'Address' = precommit_data.prev_block_contributors.get("generator")
        validators: List['Address'] = precommit_data.prev_block_contributors.get("validators")
        validators: list = []

        if generator is None or validators is None:
            return

        Logger.debug(f"put_block_produce_info_for_rc", "iiss")
        data: 'IissBlockProduceInfoData' = IissDataCreator.create_block_produce_info_data(precommit_data.block.height,
                                                                                          generator,
                                                                                          validators)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)

    @classmethod
    def _put_preps_for_rc(cls, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        if not context.prep_candidate_engine.prep_infos_dirty_include_sub_prep:
            return

        preps: List['PRep'] = context.prep_candidate_engine.get_preps_include_sub_prep()

        if len(preps) == 0:
            return

        total_candidate_delegated: int = 0
        for prep in preps:
            total_candidate_delegated += prep.total_delegated

        Logger.debug(f"put_preps_for_rc: total_candidate_delegated{total_candidate_delegated}", "iiss")

        data: 'PrepsData' = IissDataCreator.create_prep_data(precommit_data.block.height,
                                                             total_candidate_delegated,
                                                             preps)
        cls.rc_storage.put(precommit_data.rc_block_batch, data)
