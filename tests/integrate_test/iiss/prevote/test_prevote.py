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

"""Test for icon_score_base.py and icon_score_base2.py"""
from unittest.mock import Mock

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.exception import MethodNotFoundException, ServiceNotReadyException
from iconservice.icon_constant import REVISION, ConfigKey, ICX_IN_LOOP
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISS(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_get_IISS_info(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        block_height: int = self._block_height
        calc_period: int = self._config[ConfigKey.IISS_CALCULATE_PERIOD]

        # get iiss info
        response: dict = self.get_iiss_info()
        expected_response = {
            'blockHeight': block_height,
            'nextCalculation': block_height + calc_period + 1,
            'nextPRepTerm': 0,
            'variable': {
                "irep": 0,
                "rrep": 1200
            },
            'rcResult': {
            }
        }
        self.assertEqual(expected_response, response)

        block_height: int = self.make_blocks_to_end_calculation()
        self.make_blocks(block_height + 1)
        response: dict = self.get_iiss_info()
        expected_response = {
            'blockHeight': block_height + 1,
            'nextCalculation': block_height + calc_period + 1,
            'nextPRepTerm': 0,
            'variable': {
                "irep": 0,
                "rrep": 1200
            },
            'rcResult': {
                "iscore": 0,
                "estimatedICX": 0,
                "startBlockHeight": block_height - calc_period + 1,
                "endBlockHeight": block_height
            }
        }
        self.assertEqual(expected_response, response)

    def test_estimate_step_prevote(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        balance: int = 3000 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # set stake
        tx: dict = self.create_set_stake_tx(from_=self._accounts[0],
                                            value=0)
        self.estimate_step(tx)

        # set delegation
        tx: dict = self.create_set_delegation_tx(from_=self._accounts[0],
                                                 origin_delegations=[(self._accounts[0], 0)])
        self.estimate_step(tx)

        # claim iscore
        tx: dict = self.create_claim_tx(from_=self._accounts[0])
        self.estimate_step(tx)

        # register prep
        tx: dict = self.create_register_prep_tx(from_=self._accounts[0])
        self.estimate_step(tx)

        # real register prep
        self.register_prep(from_=self._accounts[0])

        # set prep
        tx: dict = self.create_set_prep_tx(from_=self._accounts[0],
                                           set_data={"name": f"new{str(self._accounts[0])}"})
        self.estimate_step(tx)

        # set governance variable
        tx: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                        irep=5_000_000)
        with self.assertRaises(MethodNotFoundException):
            self.estimate_step(tx)

        # unregister prep
        tx: dict = self.create_unregister_prep_tx(from_=self._accounts[0])
        self.estimate_step(tx)

    def test_query_prevote(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        # get stake
        response: dict = self.get_stake(self._accounts[0])
        print(response)

        # get delegation
        response: dict = self.get_delegation(self._accounts[0])
        print(response)

        # query iscore
        # mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))

        response: dict = self.query_iscore(self._accounts[0])
        print(response)

        # real register prep
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=1000 * ICX_IN_LOOP)
        self.register_prep(from_=self._accounts[0])

        # get prep
        response: dict = self.get_prep(self._accounts[0])
        print(response)

        response: dict = self.get_prep_list()
        print(response)

    def test_method_not_found(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "invalid",
                "params": {}
            }
        }

        with self.assertRaises(MethodNotFoundException):
            self._query(query_request)

    def test_prep_term(self):
        self.update_governance()
        self.set_revision(REVISION.IISS.value)

        with self.assertRaises(ServiceNotReadyException) as e:
            self.get_prep_term()
        self.assertEqual(e.exception.message, "Term is not ready")
