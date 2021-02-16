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

from typing import TYPE_CHECKING, List
from unittest.mock import Mock

from iconservice.base.address import Address, SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException, ServiceNotReadyException
from iconservice.icon_constant import ICX_IN_LOOP, Revision
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateSystemScoreInternalCall(TestIISSBase):
    """ All cases for System SCORE are tested in unit and integrate test.

    In this test, only one success case per external method of System SCORE is checked
    through inter-call to confirm System SCORE inter-call functionality.
    """
    use_interface: int = 0

    def setUp(self):
        super().setUp()
        self.update_governance()
        self.set_revision(Revision.SYSTEM_SCORE_ENABLED.value)

        self.distribute_icx(accounts=self._accounts[:10],
                            init_balance=10000 * ICX_IN_LOOP)

        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_system_score_intercall",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS,
                                                deploy_params={"use_interface": hex(self.use_interface)})

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1])
        self.score_addr: 'Address' = tx_results[0].score_address

    def test_system_score_intercall_stake(self):
        value = 1 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=value * 3)

        # TEST: stake via 'setStake' system SCORE inter-call
        self.score_call(from_=self._accounts[0],
                        to_=self.score_addr,
                        value=value,
                        func_name="call_setStake",
                        params={"value": hex(value)})

        # check stake result via 'getStake' system SCORE inter-call
        expected_response = {'stake': value}
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getStake",
                                    params={"address": str(self.score_addr)})
        self.assertEqual(expected_response, response)

        # check unstake lock period via 'estimateUnstakeLockPeriod' system SCORE inter-call
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_estimateUnstakeLockPeriod",
                                    params={})
        self.assertTrue("unstakeLockPeriod" in response)

    def test_system_score_intercall_delegation(self):
        max_delegations: int = 10
        value = 1 * ICX_IN_LOOP
        stake = value * max_delegations
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=stake)

        self.score_call(from_=self._accounts[0],
                        to_=self.score_addr,
                        value=stake,
                        func_name="call_setStake",
                        params={"value": hex(stake)})

        # TEST: delegate via 'setDelegation' system SCORE inter-call
        # set delegation 1 icx addr0 ~ addr9
        delegation_amount: int = value
        total_delegating: int = 0
        delegations: list = []
        start_index: int = 0
        for i in range(max_delegations):
            delegation_info: dict = \
                {
                    "address": str(self._accounts[start_index + i].address),
                    "value": hex(delegation_amount)
                }
            delegations.append(delegation_info)
            total_delegating += delegation_amount

        self.score_call(from_=self._accounts[0],
                        to_=self.score_addr,
                        func_name="call_setDelegation",
                        params={"delegations": delegations})

        # check delegation result with 'getStake' system SCORE inter-call
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getDelegation",
                                    params={"address": str(self.score_addr)})
        expected_response: list = [
            {
                "address": Address.from_string(d["address"]),
                "value": int(d["value"], 16)
            } for d in delegations
        ]
        self.assertEqual(expected_response, response["delegations"])
        self.assertEqual(total_delegating, response["totalDelegated"])

    def test_system_score_intercall_iScore(self):
        """ Use mocking for Reward Calculator IPC.
        This is because IPC is not allowed in integrate test environment.
        """
        iscore = 2000
        icx = iscore // 1000
        block_height = 100

        # TEST: queryIScore
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_queryIScore",
                                    params={"address": str(self.score_addr)})
        expected_response = {
            "iscore": iscore,
            "estimatedICX": icx,
            "blockHeight": block_height
        }
        self.assertEqual(expected_response, response)

        # TEST: claimIScore
        RewardCalcProxy.claim_iscore = Mock(return_value=(iscore, block_height))
        tx_result = self.score_call(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_claimIScore",
                                    params={})
        event_log = tx_result[0].event_logs[0]
        self.assertEqual([iscore, icx], event_log.data)
        self.assertEqual(["IScoreClaimedV2(Address,int,int)", self.score_addr], event_log.indexed)
        self.assertEqual(SYSTEM_SCORE_ADDRESS, event_log.score_address)

    def test_system_score_intercall_getIISSInfo(self):
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getIISSInfo",
                                    params={})
        self.assertTrue("blockHeight" in response)
        self.assertTrue("nextCalculation" in response)
        self.assertTrue("nextPRepTerm" in response)
        self.assertTrue("rcResult" in response)
        self.assertTrue("variable" in response)

    def test_system_score_intercall_getPRep(self):
        with self.assertRaises(InvalidParamsException):
            self.query_score(from_=self._accounts[0],
                             to_=self.score_addr,
                             func_name="call_getPRep",
                             params={"address": str(self.score_addr)})

    def test_system_score_intercall_getPReps(self):
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getPReps",
                                    params={"startRanking": hex(1), "endRanking": hex(100)})
        self.assertTrue("blockHeight" in response, response)
        self.assertTrue("startRanking" in response, response)
        self.assertTrue("totalDelegated" in response, response)
        self.assertTrue("totalStake" in response, response)
        self.assertTrue("preps" in response, response)

    def test_system_score_intercall_getMainPRep(self):
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getMainPReps",
                                    params={})
        self.assertTrue("totalDelegated" in response, response)
        self.assertTrue("preps" in response, response)

    def test_system_score_intercall_getSubPRep(self):
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getSubPReps",
                                    params={})
        self.assertTrue("totalDelegated" in response, response)
        self.assertTrue("preps" in response, response)

    def test_system_score_intercall_getPRepTerm(self):
        with self.assertRaises(ServiceNotReadyException):
            self.query_score(from_=self._accounts[0],
                             to_=self.score_addr,
                             func_name="call_getPRepTerm",
                             params={})

    def test_system_score_intercall_getScoreDepositInfo(self):
        response = self.query_score(from_=self._accounts[0],
                                    to_=self.score_addr,
                                    func_name="call_getScoreDepositInfo",
                                    params={"address": str(self.score_addr)})
        self.assertEqual(None, response)

    def test_system_score_intercall_burn(self):
        self.set_revision(Revision.BURN_V2_ENABLED.value)

        account = self._accounts[0]
        value = 10 * ICX_IN_LOOP
        old_total_supply: int = self.get_total_supply()

        self.transfer_icx(from_=self._admin, to_=account, value=value)

        icx_to_burn = 5 * ICX_IN_LOOP
        tx_results = self.score_call(
            from_=account,
            to_=self.score_addr,
            func_name="call_burn",
            value=icx_to_burn
        )
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status == 1)
        # ICXTransfer, ICXBurnedV2
        self.assertEqual(2, len(tx_result.event_logs))

        event_log = tx_result.event_logs[0]
        self.assertEqual(
            [
                "ICXTransfer(Address,Address,int)",
                self.score_addr,
                SYSTEM_SCORE_ADDRESS,
                icx_to_burn,
            ],
            event_log.indexed
        )

        event_log = tx_result.event_logs[1]
        self.assertEqual(
            ["ICXBurnedV2(Address,int,int)", self.score_addr],
            event_log.indexed
        )
        self.assertEqual(SYSTEM_SCORE_ADDRESS, event_log.score_address)
        self.assertEqual([icx_to_burn, old_total_supply - icx_to_burn], event_log.data)


class TestIntegrateSystemScoreInternalCallWithInterface(TestIntegrateSystemScoreInternalCall):
    use_interface = 1


class TestIntegrateSystemScoreInternalCallNotSupport(TestIISSBase):
    use_interface = 0

    def setUp(self):
        super().setUp()
        self.update_governance()
        self.set_revision(Revision.SYSTEM_SCORE_ENABLED.value - 1)

        self.distribute_icx(accounts=self._accounts[:10],
                            init_balance=10000 * ICX_IN_LOOP)

        tx1: dict = self.create_deploy_score_tx(score_root="sample_internal_call_scores",
                                                score_name="sample_system_score_intercall",
                                                from_=self._accounts[0],
                                                to_=SYSTEM_SCORE_ADDRESS,
                                                deploy_params={"use_interface": hex(self.use_interface)})

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1])
        self.score_addr: 'Address' = tx_results[0].score_address

    def test_system_score_intercall_revision(self):
        value = 1 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=value * 3)

        # TEST: stake via 'setStake' system SCORE inter-call
        self.score_call(from_=self._accounts[0],
                        to_=self.score_addr,
                        value=value,
                        func_name="call_setStake",
                        params={"value": hex(value)},
                        expected_status=False)


class TestIntegrateSystemScoreInternalCallNotSupportWithInterface(TestIntegrateSystemScoreInternalCallNotSupport):
    use_interface = 1
