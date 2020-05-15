# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

"""IconScoreEngine testcase
"""

from typing import TYPE_CHECKING
from unittest.mock import Mock

from iconservice import AddressPrefix
from iconservice.base.block import Block
from iconservice.icon_constant import ConfigKey, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.issue.base_transaction_creator import BaseTransactionCreator
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from iconservice.utils import icx_to_loop
from tests import create_block_hash, create_timestamp, create_address, create_tx_hash
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


class TestChangeBlockHash(TestIISSBase):

    def _create_base_transaction(self):
        context = IconScoreContext(IconScoreContextType.DIRECT)
        context._preps = context.engine.prep.preps.copy(mutable=True)
        context._term = context.engine.prep.term.copy()
        block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()
        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
        context.block = block
        transaction = BaseTransactionCreator.create_base_transaction(context)
        return transaction

    def test_change_block_hash_before_iiss1(self):
        tx_list = []
        tx = self.create_transfer_icx_tx(
            from_=self._admin,
            to_=self._accounts[0],
            value=icx_to_loop(1)
        )
        tx_list.append(tx)

        block, _ = self.make_and_req_block(tx_list=tx_list)
        new_block_hash = create_block_hash()
        self._write_precommit_state_leader(
            block_height=block.height,
            old_block_hash=block.hash,
            new_block_hash=new_block_hash
        )

        self.assertEqual(self.get_last_block().hash, new_block_hash)
        self.assertEqual(IconScoreContext.storage.icx.last_block.hash, new_block_hash)

    def test_change_block_hash_after_iiss1(self):
        self.init_decentralized()

        tx_list = []
        tx = self.create_transfer_icx_tx(
            from_=self._admin,
            to_=self._accounts[0],
            value=icx_to_loop(1)
        )
        tx_list.append(tx)

        block, _ = self.make_and_req_block(tx_list=tx_list)
        new_block_hash = create_block_hash()
        self._write_precommit_state_leader(
            block_height=block.height,
            old_block_hash=block.hash,
            new_block_hash=new_block_hash
        )

        self.assertEqual(self.get_last_block().hash, new_block_hash)
        self.assertEqual(IconScoreContext.storage.icx.last_block.hash, new_block_hash)

    def test_change_block_hash3(self):
        """
        about commit, rollback
        :return:
        """
        self.init_decentralized()

        self.transfer_icx(from_=self._admin.address,
                          to_=self._accounts[0],
                          value=icx_to_loop(1))

        tx_list = []
        tx = self.create_transfer_icx_tx(
            from_=self._admin,
            to_=self._accounts[0],
            value=icx_to_loop(5)
        )
        tx_list.append(tx)

        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.claim_iscore = Mock(
            return_value=(iscore, block_height))
        RewardCalcProxy.commit_claim = Mock()

        tx = self.create_claim_tx(from_=self._accounts[0])
        tx_list.append(tx)

        last_block = self.get_last_block()
        block, tx_rets = self.make_and_req_block(
            tx_list=tx_list
        )

        new_hash: bytes = create_block_hash()

        self._write_precommit_state_leader(
            block_height=block.height,
            old_block_hash=block.hash,
            new_block_hash=new_hash
        )

        m = RewardCalcProxy.commit_block
        actual_height = m.call_args[0][1]
        actual_hash = m.call_args[0][2]

        assert block.height == actual_height
        assert block.hash == actual_hash

        m = RewardCalcProxy.commit_claim
        actual_height = m.call_args[0][2]
        actual_hash = m.call_args[0][3]

        assert block.height == actual_height
        assert block.hash == actual_hash

        RewardCalcProxy.rollback = Mock(
            return_value=(True, last_block.height, last_block.hash))

        self.rollback(block_height=last_block.height,
                      block_hash=last_block.hash)

        m = RewardCalcProxy.rollback
        actual_height = m.call_args[0][0]
        actual_hash = m.call_args[0][1]

        assert last_block.height == actual_height
        assert last_block.hash == actual_hash
