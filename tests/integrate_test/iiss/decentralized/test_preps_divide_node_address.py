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
from typing import TYPE_CHECKING, Dict, Union

from iconservice import Address
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ICX_IN_LOOP, PREP_MAIN_PREPS, ConfigKey, Revision
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_address
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    pass


class TestPRepNodeAddressDivision(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()

    def test_prep_register_node_address_before_rev_DIVIDE_NODE_ADDRESS(self):
        account: 'EOAAccount' = self.create_eoa_account()
        self.distribute_icx(accounts=[account],
                            init_balance=1 * ICX_IN_LOOP)

        dummy_node: 'Address' = create_address()

        # register prep
        reg_data: dict = self.create_register_prep_params(account)
        reg_data["nodeAddress"] = str(dummy_node)

        tx: dict = self.create_register_prep_tx(from_=account,
                                                reg_data=reg_data)

        _, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx])
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[1].failure.message,
                         f"nodeAddress not supported: revision={Revision.DECENTRALIZATION.value}")

    def test_prep_set_node_address_before_rev_DIVIDE_NODE_ADDRESS(self):
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        account: 'EOAAccount' = self._accounts[0]
        dummy_node: 'Address' = create_address()

        # set prep 1
        tx: dict = self.create_set_prep_tx(from_=account,
                                           set_data={"nodeAddress": str(dummy_node)})

        _, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx])
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(tx_results[1].failure.message,
                         f"nodeAddress not supported: revision={Revision.DECENTRALIZATION.value}")

    def test_prep_register_node_address(self):
        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)
        account: 'EOAAccount' = self.create_eoa_account()
        self.distribute_icx(accounts=[account],
                            init_balance=1 * ICX_IN_LOOP)

        dummy_node: 'Address' = create_address()

        # register prep
        reg_data: dict = self.create_register_prep_params(account)
        reg_data["nodeAddress"] = str(dummy_node)

        tx: dict = self.create_register_prep_tx(from_=account,
                                                reg_data=reg_data)

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx])
        self.assertEqual(tx_results[1].status, True)

        self._write_precommit_state(block)

        ret: dict = self.get_prep(account.address)
        self.assertEqual(str(ret['nodeAddress']), reg_data['nodeAddress'])

    def test_prep_set_node_address(self):
        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        account: 'EOAAccount' = self._accounts[0]
        dummy_node: 'Address' = create_address()

        # set prep 1
        tx: dict = self.create_set_prep_tx(from_=account,
                                           set_data={"nodeAddress": str(dummy_node)})

        _, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx])
        self.assertEqual(tx_results[1].status, True)
        self.assertEqual(next_preps["preps"][0]["id"], dummy_node)

    def test_prep_set_node_address_check_generator(self):
        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # 0 start change node_address
        account: 'EOAAccount' = self._accounts[0]

        dummy_cnt: int = 3
        dummy_addrs: list = [x.address for x in self.create_eoa_accounts(dummy_cnt)]
        last_dummy_addr: 'Address' = dummy_addrs[dummy_cnt - 1]

        # set node key 3times in 1 block
        # check prev_node_key_mapper override or not
        tx_list: list = []
        for i in range(dummy_cnt):
            tx_list.append(self.create_set_prep_tx(from_=account,
                                                   set_data={"nodeAddress": str(dummy_addrs[i])}))

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        for i in range(dummy_cnt):
            self.assertEqual(tx_results[i + 1].status, True)

        self.assertEqual(next_preps["preps"][0]["id"], last_dummy_addr)
        self._write_precommit_state(block)

        # 1 before change node_address
        prev_block_generator = self._accounts[0].address
        prev_block_votes = [(x.address, True) for x in self._accounts[1:PREP_MAIN_PREPS]]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[],
                                                                                   prev_block_generator=prev_block_generator,
                                                                                   prev_block_validators=None,
                                                                                   prev_block_votes=prev_block_votes,
                                                                                   block=None)
        self.assertEqual(tx_results[0].status, True)
        self.assertEqual(next_preps, None)

        self._write_precommit_state(block)

        # 2 after change node_address
        dummy_node2: 'Address' = create_address()
        prev_block_generator = last_dummy_addr

        # set prep 2
        tx: dict = self.create_set_prep_tx(from_=account,
                                           set_data={"nodeAddress": str(dummy_node2)})

        prev_block_votes = [(x.address, True) for x in self._accounts[1:PREP_MAIN_PREPS]]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx],
                                                                                   prev_block_generator=prev_block_generator,
                                                                                   prev_block_validators=None,
                                                                                   prev_block_votes=prev_block_votes,
                                                                                   block=None)
        self.assertEqual(tx_results[0].status, True)
        self.assertEqual(next_preps["preps"][0]["id"], dummy_node2)
        self._write_precommit_state(block)

    def test_prep_set_node_address_check_votes(self):
        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # 0 start change node_key
        account: 'EOAAccount' = self._accounts[1]
        dummy_cnt: int = 3
        dummy_addrs: list = [x.address for x in self.create_eoa_accounts(dummy_cnt)]
        last_dummy_addr: 'Address' = dummy_addrs[dummy_cnt - 1]

        # set node key 3times in 1 block
        # check prev_node_key_mapper override or not
        tx_list: list = []

        for i in range(dummy_cnt):
            tx_list.append(self.create_set_prep_tx(from_=account,
                                                   set_data={"nodeAddress": str(dummy_addrs[i])}))

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        for i in range(dummy_cnt):
            self.assertEqual(tx_results[i + 1].status, True)
        self.assertEqual(next_preps["preps"][1]["id"], last_dummy_addr)
        self._write_precommit_state(block)

        # 1 before change node_address
        prev_block_generator = self._accounts[0].address
        prev_block_votes = [(x.address, True) for x in self._accounts[1:PREP_MAIN_PREPS]]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[],
                                                                                   prev_block_generator=prev_block_generator,
                                                                                   prev_block_validators=None,
                                                                                   prev_block_votes=prev_block_votes,
                                                                                   block=None)
        self.assertEqual(tx_results[0].status, True)
        self.assertEqual(next_preps, None)

        self._write_precommit_state(block)

        # 2 after change node_address
        dummy_node2: 'Address' = create_address()
        prev_block_generator = last_dummy_addr

        # set prep 2
        tx: dict = self.create_set_prep_tx(from_=account,
                                           set_data={"nodeAddress": str(dummy_node2)})

        prev_block_votes = [(x.address, True) for x in self._accounts[1:PREP_MAIN_PREPS]]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=[tx],
                                                                                   prev_block_generator=prev_block_generator,
                                                                                   prev_block_validators=None,
                                                                                   prev_block_votes=prev_block_votes,
                                                                                   block=None)
        self.assertEqual(tx_results[0].status, True)
        self.assertEqual(next_preps["preps"][1]["id"], dummy_node2)
        self._write_precommit_state(block)

    def test_scenario1(self):
        # PRepA a ---- a
        # PRepB b ---- b

        # after 1 block
        # PRepA a ---- a
        # PRepB b ---- a (fail)

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # PRepA: 0
        # PRepB: 1
        prep_b: 'EOAAccount' = self._accounts[1]
        prep_a: 'Address' = self._accounts[0].address
        tx_list: list = [self.create_set_prep_tx(from_=prep_b,
                                                 set_data={"nodeAddress": str(prep_a)})]

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, False)
        self.assertEqual(tx_results[1].failure.message, f"nodeAddress already in use: {str(prep_a)}")

    def test_scenario2(self):
        # PRepA a ---- a

        # after 1 block
        # PRepA a ---- a1

        # after 2 block
        # PRepA a ---- a

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # PRepA: 0
        prep_a: 'EOAAccount' = self._accounts[0]
        old_addr: 'Address' = self._accounts[0].address
        new_addr: 'Address' = create_address()

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(new_addr)})]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)
        self._write_precommit_state(block)

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(old_addr)})]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)

    def test_scenario3(self):
        # PRepA a ---- a
        # PRepB b ---- b

        # after 1 block
        # PRepA a ---- a1

        # after 2 block
        # PRepA a ---- a2
        # PRepB b ---- a1

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # PRepA: 0
        # PRepB: 1
        prep_a: 'EOAAccount' = self._accounts[0]
        prep_a_new_addr1: 'Address' = create_address()
        prep_a_new_addr2: 'Address' = create_address()
        prep_b: 'EOAAccount' = self._accounts[1]

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(prep_a_new_addr1)})]
        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)
        self._write_precommit_state(block)

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(prep_a_new_addr2)}),
                         self.create_set_prep_tx(from_=prep_b,
                                                 set_data={"nodeAddress": str(prep_a_new_addr1)})]

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)
        self.assertEqual(tx_results[2].status, True)

    def test_scenario4(self):
        # 1 block
        # PRepA a ---- a
        # PRepB b ---- b
        # unreg PRepB

        # after 1 block
        # PRepA a ---- b

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        # PRepA: 0
        # PRepB: 1
        prep_a: 'EOAAccount' = self._accounts[0]
        prep_b: 'EOAAccount' = self._accounts[1]

        tx_list: list = [self.create_unregister_prep_tx(from_=prep_b),
                         self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(prep_b.address)})]

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)
        self.assertEqual(tx_results[2].status, True)

    def test_scenario5(self):
        # 1 block
        # PRepA a ---- a
        # PRepB b ---- b
        # penalty PRepB (low productivity)

        # after 1 block
        # PRepA a ---- b

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        PREV_PENALTY_GRACE_PERIOD = IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period
        PREV_LOW_PRODUCTIVITY_PENALTY_THRESHOLD = \
            IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold

        PENALTY_GRACE_PERIOD = 0
        # enable low productivity
        LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 100

        IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period = PENALTY_GRACE_PERIOD
        IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold = \
            LOW_PRODUCTIVITY_PENALTY_THRESHOLD

        votes = [[self._accounts[1].address, False]] + \
                [[account.address, True] for account in self._accounts[2:PREP_MAIN_PREPS]]
        tx_results = self.make_blocks(to=self._block_height + 2,
                                      prev_block_generator=self._accounts[0].address,
                                      prev_block_votes=votes)

        IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period = PREV_PENALTY_GRACE_PERIOD
        IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold = \
            PREV_LOW_PRODUCTIVITY_PENALTY_THRESHOLD

        # PRepA: 0
        # PRepB: 1
        prep_a: 'EOAAccount' = self._accounts[0]
        prep_b: 'EOAAccount' = self._accounts[1]

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(prep_b.address)})]

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, True)

        # Before calling write_precommit_state()
        ret: Dict[str, Union[str, int, bytes, 'Address']] = self.get_prep(prep_a)
        assert ret["nodeAddress"] == prep_a.address

        self._write_precommit_state(block)

        # After calling write_precommit_state()
        ret: Dict[str, Union[str, int, bytes, 'Address']] = self.get_prep(prep_a)
        assert ret["nodeAddress"] == prep_b.address

    def test_scenario6(self):
        # 1 block
        # PRepA a ---- a
        # PRepB b ---- b
        # penalty PRepB (turn over)

        # after 1 block
        # PRepA a ---- b (fail)

        self.set_revision(Revision.DIVIDE_NODE_ADDRESS.value)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

        PREV_PENALTY_GRACE_PERIOD = IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period
        PREV_BLOCK_VALIDATION_PENALTY_THRESHOLD = \
            IconScoreContext.engine.prep._penalty_imposer._block_validation_penalty_threshold
        PREV_LOW_PRODUCTIVITY_PENALTY_THRESHOLD = \
            IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold

        PENALTY_GRACE_PERIOD = 0
        # disable low productivity
        LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 0
        # enable block validation
        BLOCK_VALIDATION_PENALTY_THRESHOLD = 1

        IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period = PENALTY_GRACE_PERIOD
        IconScoreContext.engine.prep._penalty_imposer._block_validation_penalty_threshold = \
            BLOCK_VALIDATION_PENALTY_THRESHOLD
        IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold = \
            LOW_PRODUCTIVITY_PENALTY_THRESHOLD

        votes = [[self._accounts[1].address, False]] + \
                [[account.address, True] for account in self._accounts[2:PREP_MAIN_PREPS]]
        tx_results = self.make_blocks(to=self._block_height + 2,
                                      prev_block_generator=self._accounts[0].address,
                                      prev_block_votes=votes)

        IconScoreContext.engine.prep._penalty_imposer._penalty_grace_period = PREV_PENALTY_GRACE_PERIOD
        IconScoreContext.engine.prep._penalty_imposer._block_validation_penalty_threshold = \
            PREV_BLOCK_VALIDATION_PENALTY_THRESHOLD
        IconScoreContext.engine.prep._penalty_imposer._low_productivity_penalty_threshold = \
            PREV_LOW_PRODUCTIVITY_PENALTY_THRESHOLD

        # PRepA: 0
        # PRepB: 1
        prep_a: 'EOAAccount' = self._accounts[0]
        prep_b: 'EOAAccount' = self._accounts[1]

        tx_list: list = [self.create_set_prep_tx(from_=prep_a,
                                                 set_data={"nodeAddress": str(prep_b.address)})]

        block, tx_results, _, _, next_preps = self.debug_make_and_req_block(tx_list=tx_list)
        self.assertEqual(tx_results[1].status, False)

        # Before calling write_precommit_state()
        ret: Dict[str, Union[str, int, bytes, 'Address']] = self.get_prep(prep_a)
        assert ret["nodeAddress"] == prep_a.address

        self._write_precommit_state(block)

        # After calling write_precommit_state()
        ret: Dict[str, Union[str, int, bytes, 'Address']] = self.get_prep(prep_a)
        assert ret["nodeAddress"] == prep_a.address
