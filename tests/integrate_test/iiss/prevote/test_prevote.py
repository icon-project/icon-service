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

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.base.exception import MethodNotFoundException, ServiceNotReadyException, FatalException
from iconservice.icon_constant import Revision, ConfigKey, ICX_IN_LOOP, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
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
        self.set_revision(Revision.IISS.value)

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

    def test_get_service_config(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        expected_response: dict = {'amqpKey': self._config[ConfigKey.AMQP_KEY],
                                   'amqpTarget': self._config[ConfigKey.AMQP_TARGET],
                                   'audit': self._config[ConfigKey.SERVICE][ConfigKey.SERVICE_AUDIT],
                                   'blockValidationPenaltyThreshold': self._config[ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD],
                                   'builtinScoreOwner': Address.from_string(self._config[ConfigKey.BUILTIN_SCORE_OWNER]),
                                   'channel': self._config[ConfigKey.CHANNEL],
                                   'decentralizeTrigger': self._config[ConfigKey.DECENTRALIZE_TRIGGER],
                                   'deployerWhiteList': self._config[ConfigKey.SERVICE][ConfigKey.SERVICE_DEPLOYER_WHITE_LIST],
                                   'fee': self._config[ConfigKey.SERVICE][ConfigKey.SERVICE_FEE],
                                   'iconRcPath': self._config[ConfigKey.ICON_RC_DIR_PATH],
                                   'iissCalculatePeriod': self._config[ConfigKey.IISS_CALCULATE_PERIOD],
                                   'initialIRep': self._config[ConfigKey.INITIAL_IREP],
                                   'ipcTimeout': self._config[ConfigKey.IPC_TIMEOUT],
                                   'lockMax': self._config[ConfigKey.IISS_META_DATA][ConfigKey.UN_STAKE_LOCK_MAX],
                                   'lockMin': self._config[ConfigKey.IISS_META_DATA][ConfigKey.UN_STAKE_LOCK_MIN],
                                   'lowProductivityPenaltyThreshold': self._config[ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD],
                                   'mainAndSubPRepCount': self._config[ConfigKey.PREP_MAIN_AND_SUB_PREPS],
                                   'mainPRepCount': self._config[ConfigKey.PREP_MAIN_PREPS],
                                   'penaltyGracePeriod': self._config[ConfigKey.PENALTY_GRACE_PERIOD],
                                   'precommitDataLogFlag': self._config[ConfigKey.PRECOMMIT_DATA_LOG_FLAG],
                                   'prepRegistrationFee': self._config[ConfigKey.PREP_REGISTRATION_FEE],
                                   'rewardMAX': self._config[ConfigKey.IISS_META_DATA][ConfigKey.REWARD_MAX],
                                   'rewardMin': self._config[ConfigKey.IISS_META_DATA][ConfigKey.REWARD_MIN],
                                   'rewardPoint': self._config[ConfigKey.IISS_META_DATA][ConfigKey.REWARD_POINT],
                                   'scorePackageValidator': True,
                                   'scoreRootPath': self._config[ConfigKey.SCORE_ROOT_PATH],
                                   'stateDbRootPath': self._config[ConfigKey.STATE_DB_ROOT_PATH],
                                   'stepTraceFlag': self._config[ConfigKey.STEP_TRACE_FLAG],
                                   'termPeriod': self._config[ConfigKey.TERM_PERIOD]}
        # get iiss info
        response: dict = self.get_service_config()
        self.assertEqual(expected_response, response)

    def test_estimate_step_prevote(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

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
        self.set_revision(Revision.IISS.value)

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
        self.set_revision(Revision.IISS.value)

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
        self.set_revision(Revision.IISS.value)

        with self.assertRaises(ServiceNotReadyException) as e:
            self.get_prep_term()
        self.assertEqual(e.exception.message, "Term is not ready")

    def mock_calculate(self, _path, _block_height):
        pass

    def test_check_calculate_done(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        self._mock_ipc(self.mock_calculate)

        self.make_blocks(self._block_height + self.CALCULATE_PERIOD - 1)

        with self.assertRaises(FatalException):
            self.make_blocks(self._block_height + 1)
