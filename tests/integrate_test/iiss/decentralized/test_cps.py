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

from iconservice.base.address import Address
from iconservice.icon_constant import *
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

CALC_PERIOD = 22


class TestCPS(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        config[ConfigKey.IISS_CALCULATE_PERIOD] = CALC_PERIOD
        config[ConfigKey.TERM_PERIOD] = CALC_PERIOD
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()
        self.init_inv()
        self.set_revision(Revision.LATEST.value)

        self._cps_owner: 'EOAAccount' = self.create_eoa_account()
        self._cps_contributor: 'EOAAccount' = self.create_eoa_account()

        self.distribute_icx(
            accounts=[self._cps_owner, self._cps_contributor],
            init_balance=1_000_000 * ICX_IN_LOOP
        )

        self.distribute_icx(
            accounts=[self._cps_contributor],
            init_balance=100 * ICX_IN_LOOP
        )

        self.distribute_icx(
            accounts=self._accounts[:20],
            init_balance=1_000 * ICX_IN_LOOP
        )

        txs: list = []
        for i in range(8):
            txs.append(
                self.create_set_stake_tx(
                    from_=self._accounts[i],
                    value=10 * ICX_IN_LOOP,
                )
            )

            txs.append(
                self.create_set_delegation_tx(
                    from_=self._accounts[i],
                    origin_delegations=[
                        (
                            self._accounts[i],
                            10 * ICX_IN_LOOP
                        )
                    ]
                )
            )
        self.process_confirm_block_tx(
            tx_list=txs,
            expected_status=True
        )

    def _deploy(self):
        # deploy
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="cps/CPFTreasury",
            from_=self._cps_owner,
            deploy_params={}
        )
        cpf_treasury: 'Address' = tx_results[1].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="cps/CPSTreasury",
            from_=self._cps_owner,
            deploy_params={}
        )
        cps_treasury: 'Address' = tx_results[1].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="cps/cps_score",
            from_=self._cps_owner,
            deploy_params={}
        )
        cps: 'Address' = tx_results[1].score_address
        return cpf_treasury, cps_treasury, cps

    def _link_scores(self, cpf_treasury: 'Address', cps_treasury: 'Address', cps: 'Address'):
        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cpf_treasury,
            func_name="set_cps_treasury_score",
            params={"_score": str(cps_treasury)}
        )

        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cpf_treasury,
            func_name="set_cps_score",
            params={"_score": str(cps)}
        )

        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps_treasury,
            func_name="set_cpf_treasury_score",
            params={"_score": str(cpf_treasury)}
        )

        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps_treasury,
            func_name="set_cps_score",
            params={"_score": str(cps)}
        )

        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps,
            func_name="set_cps_treasury_score",
            params={"_score": str(cps_treasury)}
        )

        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps,
            func_name="set_cpf_treasury_score",
            params={"_score": str(cpf_treasury)}
        )

    def _jump_period(self, cps: 'Address'):
        status: dict = self.query_score(
            from_=self._cps_owner,
            to_=cps,
            func_name="get_period_status"
        )
        print(f"get_period_status: {status}")
        next_block: int = status["next_block"]
        self.make_blocks(to=next_block + 1)

    def _prt_period_status(self, cps: 'Address'):
        tx_results = self.score_call(
            from_=self._accounts[0],
            to_=cps,
            func_name="update_period",
            params={}
        )
        status: dict = self.query_score(
            from_=self._cps_owner,
            to_=cps,
            func_name="get_period_status"
        )
        print(f"get_period_status: {status}")

    def test_normal(self):
        cpf_treasury, cps_treasury, cps = self._deploy()
        self._link_scores(cpf_treasury, cps_treasury, cps)

        # set fund
        init_fund: int = 10_000
        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cpf_treasury,
            value=init_fund * ICX_IN_LOOP,
            func_name="add_fund",
        )

        # set penalty
        penalty = [50, 100, 250]
        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps,
            func_name="set_prep_penalty_amount",
            params={"_penalty": [hex(p * ICX_IN_LOOP) for p in penalty]}
        )

        # register PRep
        txs: list = []
        for i in range(8):
            txs.append(
                self.create_score_call_tx(
                    from_=self._accounts[i],
                    to_=cps,
                    func_name="register_prep",
                )
            )
        self.process_confirm_block_tx(txs, True)

        total_budget: int = 100 * ICX_IN_LOOP
        ipfs_hash: str = "bafybeid3ucflkuettyzvzbsnqhvw5mtqkgbtes4s5yykhr6vd4ma7f7aiy"
        project_duration: int = 4
        proposals = {
            "project_title": "ICON Mobile Wallet",
            "total_budget": hex(total_budget),
            "sponsor_address": str(self._accounts[0].address),
            "ipfs_hash": f"{ipfs_hash}",
            "ipfs_link": "https://gateway.ipfs.io/ipfs/bafybeid3ucflkuettyzvzbsnqhvw5mtqkgbtes4s5yykhr6vd4ma7f7aiy",
            "project_duration": hex(project_duration),
        }

        # start SCORE
        tx_results = self.score_call(
            from_=self._cps_owner,
            to_=cps,
            func_name="set_initialBlock",
            params={}
        )

        # submit proposal
        tx_results = self.score_call(
            from_=self._cps_contributor,
            to_=cps,
            value=50 * ICX_IN_LOOP,
            func_name="submit_proposal",
            params={"_proposals": proposals}
        )

        is_twice_submit = False
        if is_twice_submit:
            tx_results = self.score_call(
                from_=self._cps_contributor,
                to_=cps,
                func_name="submit_proposal",
                params={"_proposals": proposals}
            )

        report_hash1: str = "Progress Report IPFS HASH Key1"
        params = {
            "report_hash": report_hash1,
            "ipfs_hash": ipfs_hash,
            "progress_report_title": "Progress Report Title",
            "ipfs_link": "IPFS Submission Link",
            "percentage_completed": hex(10),
            "budget_adjustment": hex(False),
            "additional_budget": "0",
            "additional_month": "0"
        }
        tx_results = self.score_call(
            from_=self._cps_contributor,
            to_=cps,
            func_name="submit_progress_report",
            params={"_progress_report": params}
        )

        report_hash2: str = "Progress Report IPFS HASH Key2"
        params = {
            "report_hash": report_hash2,
            "ipfs_hash": ipfs_hash,
            "progress_report_title": "Progress Report Title",
            "ipfs_link": "IPFS Submission Link",
            "percentage_completed": hex(20),
            "budget_adjustment": hex(False),
            "additional_budget": "0",
            "additional_month": "0"
        }
        tx_results = self.score_call(
            from_=self._cps_contributor,
            to_=cps,
            func_name="submit_progress_report",
            params={"_progress_report": params}
        )

        # sponsor vote (approve)
        is_sponsor_approve = True
        if is_sponsor_approve:
            tx_results = self.score_call(
                from_=self._accounts[0],
                to_=cps,
                value=10 * ICX_IN_LOOP,
                func_name="sponsor_vote",
                params={
                    "_ipfs_key": ipfs_hash,
                    "_vote": "_accept",
                }
            )

        is_sponsor_reject = False
        if is_sponsor_reject:
            tx_results = self.score_call(
                from_=self._accounts[0],
                to_=cps,
                value=10 * ICX_IN_LOOP,
                func_name="sponsor_vote",
                params={
                    "_ipfs_key": ipfs_hash,
                    "_vote": "_reject",
                }
            )

        # wait vote period
        status: dict = self.query_score(
            from_=self._cps_owner,
            to_=cps,
            func_name="get_period_status"
        )
        print(f"get_period_status: {status}")
        next_block: int = status["next_block"]
        self.make_blocks(to=next_block + 1)

        # update period
        self._jump_period(cps)
        is_update_period = True
        if is_update_period:
            self._prt_period_status(cps)

        # vote approve
        is_vote_8_approve = True
        if is_vote_8_approve:
            txs: list = []
            for i in range(8):
                txs.append(
                    self.create_score_call_tx(
                        from_=self._accounts[i],
                        to_=cps,
                        func_name="vote_proposal",
                        params={
                            "_ipfs_key": ipfs_hash,
                            "_vote": "_approve"
                        }
                    )
                )

                txs.append(
                    self.create_score_call_tx(
                        from_=self._accounts[i],
                        to_=cps,
                        func_name="vote_progress_report",
                        params={
                            "_ipfs_key": ipfs_hash,
                            "_report_key": report_hash1,
                            "_vote": "_approve"
                        }
                    )
                )
                # txs.append(
                #     self.create_score_call_tx(
                #         from_=self._accounts[i],
                #         to_=cps,
                #         func_name="vote_progress_report",
                #         params={
                #             "_ipfs_key": ipfs_hash,
                #             "_report_key": report_hash2,
                #             "_vote": "_approve"
                #         }
                #     )
                # )
            self.process_confirm_block_tx(txs, True)

        info: dict = self.query_score(
            from_=self._accounts[0],
            to_=cps,
            func_name="get_proposal_detail_by_wallet",
            params={
                "_wallet_address": str(self._cps_contributor.address),
            }
        )
        print(f"get_proposal_detail_by_wallet: {info}")

        # update period
        self._jump_period(cps)
        is_update_period = True
        if is_update_period:
            self._prt_period_status(cps)

        info: dict = self.query_score(
            from_=self._accounts[0],
            to_=cps,
            func_name="get_proposal_detail_by_wallet",
            params={
                "_wallet_address": str(self._cps_contributor.address),
            }
        )
        print(f"get_proposal_detail_by_wallet: {info}")

        info: dict = self.query_score(
            from_=self._accounts[0],
            to_=cps_treasury,
            func_name="get_contributor_projected_fund",
            params={
                "_wallet_address": str(self._cps_contributor.address),
            }
        )
        print(f"get_contributor_projected_fund: {info}")

        info: dict = self.query_score(
            from_=self._accounts[0],
            to_=cps_treasury,
            func_name="get_sponsor_projected_fund",
            params={
                "_wallet_address": str(self._accounts[0].address),
            }
        )
        print(f"get_sponsor_projected_fund: {info}")

        prev_balance = self.get_balance(self._cps_contributor)
        tx_results = self.score_call(
            from_=self._cps_contributor,
            to_=cps_treasury,
            func_name="claim_reward",
            params={}
        )
        balance = self.get_balance(self._cps_contributor)
        diff = balance - prev_balance
        print(f"diff: {diff}")
