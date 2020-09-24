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
from copy import deepcopy
from typing import TYPE_CHECKING, List

from iconservice.base.address import Address, SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_INITIAL_IREP, PRepGrade, PRepStatus, PenaltyReason
from iconservice.icon_constant import Revision, PREP_MAIN_PREPS, ConfigKey, ICX_IN_LOOP
from iconservice.prep import PRepMethod
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

name = "prep"

prep_register_data = {
    ConstantKeys.NAME: name,
    ConstantKeys.EMAIL: f"{name}@example.com",
    ConstantKeys.WEBSITE: f"https://{name}.example.com",
    ConstantKeys.DETAILS: f"https://{name}.example.com/details",
    ConstantKeys.P2P_ENDPOINT: f"{name}.example.com:7100",
    ConstantKeys.CITY: "city",
    ConstantKeys.COUNTRY: "KOR"
}


class TestIntegratePrep(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_preps(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

        # register prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_register_prep_tx(self._accounts[i])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # get prep 0 ~ PREP_MAIN_PREPS
        register_block_height: int = self.get_block_height()
        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(self._accounts[i])
            expected_params: dict = self.create_register_prep_params(self._accounts[i])
            self.assertEqual(0, response["delegated"])
            self.assertEqual(0, response["stake"])
            self.assertEqual(self._config[ConfigKey.INITIAL_IREP], response["irep"])
            self.assertEqual(register_block_height, response["irepUpdateBlockHeight"])
            for key in ("details", "email", "name", "country", "city", "p2pEndpoint", "website"):
                self.assertEqual(expected_params[key], response[key])
            self.assertEqual(0, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])
            self.assertEqual(PRepStatus.ACTIVE.value, response["status"])
            self.assertEqual(PRepGrade.CANDIDATE.value, response["grade"])

        # set prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_prep_tx(from_=self._accounts[i],
                                               set_data={"name": f"{self._accounts[i]}"})
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # get prep 0 ~ PREP_MAIN_PREPS
        for i in range(PREP_MAIN_PREPS):
            account = self._accounts[i]

            response: dict = self.get_prep(account)
            expected_params: dict = self.create_register_prep_params(account)
            expected_response: dict = {
                "address": account.address,
                "delegated": 0,
                "stake": 0,
                "details": expected_params["details"],
                "email": expected_params["email"],
                "irep": self._config[ConfigKey.INITIAL_IREP],
                "irepUpdateBlockHeight": register_block_height,
                "lastGenerateBlockHeight": -1,
                "name": f"{account}",
                "country": expected_params["country"],
                "city": expected_params["city"],
                "p2pEndpoint": expected_params['p2pEndpoint'],
                "website": expected_params['website'],
                "totalBlocks": 0,
                "validatedBlocks": 0,
                "status": PRepStatus.ACTIVE.value,
                "grade": PRepGrade.CANDIDATE.value,
                "penalty": PenaltyReason.NONE.value,
                "unvalidatedSequenceBlocks": 0,
                "blockHeight": register_block_height,
                "txIndex": i,
                "nodeAddress": account.address
            }
            self.assertEqual(expected_response, response)

        # unregister prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_unregister_prep_tx(self._accounts[i])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        response: dict = self.get_prep_list()
        expected_response: dict = {
            "blockHeight": self._block_height,
            "startRanking": 1,
            "totalDelegated": 0,
            "totalStake": 0,
            "preps": []
        }
        self.assertEqual(expected_response, response)

    def test_get_prep_list(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        prep_count: int = 3000
        accounts: list = self.create_eoa_accounts(prep_count)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # register prep
        tx_list: list = []
        for i in range(prep_count):
            tx: dict = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(start_ranking=-1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(end_ranking=-1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(0, 1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(1, 0)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(2, 1)

        response: dict = self.get_prep_list(2, 2)
        actual_preps: list = response['preps']
        self.assertEqual(1, len(actual_preps))

        response: dict = self.get_prep_list()
        actual_preps: list = response['preps']
        self.assertEqual(prep_count, len(actual_preps))

        response: dict = self.get_prep_list(start_ranking=1)
        actual_preps: list = response['preps']
        self.assertEqual(prep_count, len(actual_preps))

    def test_preps_and_delegated(self):
        max_delegations: int = 10
        self.maxDiff = None
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

        # register prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_register_prep_tx(self._accounts[i])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)
        register_block_height: int = self.get_block_height()
        irep_update_block_height: int = register_block_height

        # gain 10 icx user0
        balance: int = 100 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=balance)

        # stake 10 icx user0
        stake_amount: int = 10 * ICX_IN_LOOP
        self.set_stake(from_=self._accounts[0],
                       value=stake_amount)

        # delegation 1 icx user0 ~ 9
        delegations: list = []
        delegation_amount: int = 1 * ICX_IN_LOOP
        for i in range(max_delegations):
            delegations.append((self._accounts[i], delegation_amount))
        self.set_delegation(from_=self._accounts[0],
                            origin_delegations=delegations)

        response: dict = self.get_main_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_sub_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_prep_list(end_ranking=max_delegations)
        preps: list = []
        for i in range(max_delegations):
            address: 'Address' = self._accounts[i].address
            expected_params: dict = self.create_register_prep_params(self._accounts[i])
            preps.append(
                {
                    "status": 0,
                    "grade": PRepGrade.CANDIDATE.value,
                    "country": "KOR",
                    "city": "Unknown",
                    "address": address,
                    "name": str(self._accounts[i]),
                    "lastGenerateBlockHeight": -1,
                    "stake": stake_amount if i == 0 else 0,
                    "delegated": delegation_amount,
                    "irep": IISS_INITIAL_IREP,
                    "irepUpdateBlockHeight": irep_update_block_height,
                    "totalBlocks": 0,
                    "validatedBlocks": 0,
                    "penalty": PenaltyReason.NONE.value,
                    "unvalidatedSequenceBlocks": 0,
                    "blockHeight": register_block_height,
                    "txIndex": i,
                    "email": expected_params["email"],
                    "website": expected_params["website"],
                    "details": expected_params["details"],
                    "p2pEndpoint": expected_params["p2pEndpoint"],
                    "nodeAddress": address
                }
            )

        expected_response: dict = \
            {
                "blockHeight": self._block_height,
                "startRanking": 1,
                "totalDelegated": stake_amount,
                "totalStake": stake_amount,
                "preps": preps,
            }
        self.assertEqual(expected_response, response)

    # TODO
    def test_prep_fail1(self):
        pass

    def test_set_governance_variables_failure(self):
        """setGovernanceVariable request causes MethodNotFound exception under prevoting revision

        :return:
        """
        self.update_governance()

        prep_address: 'Address' = self._accounts[0]

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # distribute icx for prep
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=3000 * ICX_IN_LOOP)

        self.register_prep(self._accounts[0])

        # get prep
        response = self.get_prep(prep_address)
        self.assertEqual(IISS_INITIAL_IREP, response[ConstantKeys.IREP])

        irep: int = response[ConstantKeys.IREP]

        # setGovernanceVariables call should be failed until IISS decentralization feature is enabled
        tx_results: List['TransactionResult'] = self.set_governance_variables(from_=self._accounts[0],
                                                                              irep=irep + 10,
                                                                              expected_status=False)
        self.assertEqual(ExceptionCode.METHOD_NOT_FOUND, tx_results[0].failure.code)

    def test_reg_prep_validator(self):
        self.update_governance()

        # set Revision REV_IISS
        revision = Revision.IISS.value
        self.set_revision(revision)

        # gain 10 icx user0
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:8],
                            init_balance=balance)
        reg_data = deepcopy(prep_register_data)
        self._validate_name(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_email(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_website(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_country(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_city(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_details(reg_data)
        reg_data = deepcopy(prep_register_data)
        self._validate_p2p_endpoint(reg_data, revision)

    def test_reg_prep_validator_fixed_email_validation(self):
        self.update_governance()

        # set Revision REV_FIX_EMAIL_REGEX
        revision = Revision.FIX_EMAIL_VALIDATION.value
        self.set_revision(revision)

        # gain 10 icx user0
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:8],
                            init_balance=balance)

        reg_data = deepcopy(prep_register_data)
        self._validate_name(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("a")
        reg_data[ConstantKeys.EMAIL] = '你好@validexample.com'
        self._validate_fixed_email(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("b")
        self._validate_website(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("c")
        self._validate_country(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("d")
        self._validate_city(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("e")
        self._validate_details(reg_data)
        reg_data = self.get_prep_data_with_customized_endpoint("f")
        self._validate_p2p_endpoint(reg_data, revision)

    def test_prevent_duplicated_endpoint(self):
        self.update_governance()

        # set Revision REV_FIX_EMAIL_REGEX
        revision = Revision.PREVENT_DUPLICATED_ENDPOINT.value
        self.set_revision(revision)

        # gain 10 icx user0
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:2],
                            init_balance=balance)

        # register prep1
        prep1_data = deepcopy(prep_register_data)
        tx = self.create_register_prep_tx(self._accounts[0], prep1_data)
        self.process_confirm_block_tx([tx])

        # fail to register due to duplicated endpoint
        tx = self.create_register_prep_tx(self._accounts[1], prep1_data)
        self.process_confirm_block_tx([tx], expected_status=False)

        # success to register prep2
        prep2_data = deepcopy(prep1_data)
        prep2_data[ConstantKeys.P2P_ENDPOINT] = "node2.endpoint:7100"
        tx = self.create_register_prep_tx(self._accounts[1], prep2_data)
        self.process_confirm_block_tx([tx], expected_status=True)

        # success to set prep
        prep1_endpoint_ip = "1.2.3.4:7100"
        prep1_data[ConstantKeys.NAME] = "name2"
        prep1_data[ConstantKeys.P2P_ENDPOINT] = "1.2.3.4:7100"
        tx = self.create_set_prep_tx(self._accounts[0], prep1_data)
        self.process_confirm_block_tx([tx], expected_status=True)

        # fail to setPRep due to duplicated endpoint(used by prep1)
        prep2_data = deepcopy(prep1_data)
        prep2_data[ConstantKeys.P2P_ENDPOINT] = prep1_endpoint_ip
        tx = self.create_set_prep_tx(self._accounts[1], prep2_data)
        self.process_confirm_block_tx([tx], expected_status=False)


    @staticmethod
    def get_prep_data_with_customized_endpoint(key: str):
        """Written for revision >= 9 since from revision 9, disallows duplicated endpoint"""
        reg_data = deepcopy(prep_register_data)
        reg_data[ConstantKeys.P2P_ENDPOINT] = f"{key}1.example.com:7100"
        return reg_data

    def _validate_name(self, reg_data: dict):
        tx = self.create_register_prep_tx(self._accounts[0], reg_data)
        self.process_confirm_block_tx([tx])

        reg_data[ConstantKeys.NAME] = ''
        tx = self.create_register_prep_tx(self._accounts[0], reg_data)
        self.process_confirm_block_tx([tx],
                                      expected_status=False)

    def _validate_email(self, reg_data: dict):
        reg_data[ConstantKeys.EMAIL] = "valid@validexample.com"
        tx = self.create_register_prep_tx(self._accounts[1], reg_data)
        self.process_confirm_block_tx([tx])

        invalid_email_list = ['', 'invalid email', 'invalid.com', 'invalid@', 'invalid@a', 'invalid@a.',
                              'invalid@.com']

        for email in invalid_email_list:
            reg_data[ConstantKeys.EMAIL] = email
            tx = self.create_register_prep_tx(self._accounts[1], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

    def _validate_fixed_email(self, reg_data: dict):
        tx = self.create_register_prep_tx(self._accounts[1], reg_data)
        self.process_confirm_block_tx([tx])
        registered_data = self.get_prep(self._accounts[1])
        self.assertEqual(reg_data[ConstantKeys.EMAIL], registered_data['email'])
        invalid_email_list = ['invalid email', 'invalid.com', 'invalid@', f"{'a'*65}@example.com",
                              f"{'a'*253}@aa", '@invalid', f'{"가"*64}@example.com']

        for email in invalid_email_list:
            reg_data[ConstantKeys.EMAIL] = email
            tx = self.create_register_prep_tx(self._accounts[1], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

    def _validate_website(self, reg_data: dict):
        tx = self.create_register_prep_tx(self._accounts[2], reg_data)
        self.process_confirm_block_tx([tx])

        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        reg_data: dict = deepcopy(prep_register_data)
        for website in invalid_website_list:
            reg_data[ConstantKeys.WEBSITE] = website
            tx = self.create_register_prep_tx(self._accounts[2], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

    # TODO
    def _validate_country(self, reg_data: dict):
        pass

    # TODO
    def _validate_city(self, reg_data: dict):
        pass

    def _validate_details(self, reg_data: dict):
        tx = self.create_register_prep_tx(self._accounts[5], reg_data)
        self.process_confirm_block_tx([tx])

        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        reg_data: dict = deepcopy(prep_register_data)
        for website in invalid_website_list:
            reg_data[ConstantKeys.WEBSITE] = website
            tx = self.create_register_prep_tx(self._accounts[5], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

    def _validate_p2p_endpoint(self, reg_data: dict, revision: int):
        tx = self.create_register_prep_tx(self._accounts[6], reg_data)
        self.process_confirm_block_tx([tx])

        if revision >= Revision.PREVENT_DUPLICATED_ENDPOINT.value:
            tx = self.create_register_prep_tx(self._accounts[6], reg_data)
            self.process_confirm_block_tx([tx], expected_status=False)

        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."
                                                                                    "https://target.asdf:7100"]

        for website in invalid_website_list:
            reg_data[ConstantKeys.P2P_ENDPOINT] = website
            tx = self.create_register_prep_tx(self._accounts[6], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

    def test_prep_stake(self):
        """Test P-Rep stake management
        """

        # Update governance SCORE
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        prep_count = 30
        user_account: 'EOAAccount' = self.create_eoa_accounts(1)[0]
        accounts: List['EOAAccount'] = self.create_eoa_accounts(prep_count)

        # Transfer 100 icx to 30 prep addresses and one user address
        tx_list: list = [
            self.create_transfer_icx_tx(self._admin, user_account, 100 * ICX_IN_LOOP)
        ]
        for i in range(prep_count):
            prep_address: 'Address' = accounts[i]
            assert user_account != prep_address

            tx: dict = self.create_transfer_icx_tx(self._admin, prep_address, 3000 * ICX_IN_LOOP)
            tx_list.append(tx)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list)
        self.assertEqual(prep_count + 1, len(tx_results))

        # Register 30 P-Rep candidates
        tx_list: list = []
        for account in accounts:
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # Check whether the stake of each P-Rep is 0
        response: dict = self.get_prep_list(start_ranking=1)
        preps: list = response["preps"]
        self.assertEqual(prep_count, len(preps))
        for prep in preps:
            self.assertEqual(0, prep["stake"])

        # Change the stake of each P-Rep
        total_stake: int = 0
        tx_list = []
        for i, account in enumerate(accounts):
            stake: int = i * 10 * ICX_IN_LOOP
            total_stake += stake

            tx = self.create_set_stake_tx(from_=account,
                                          value=stake)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # Check whether the stake of each P-Rep is correct.
        response: dict = self.get_prep_list(start_ranking=1)
        self.assertEqual(total_stake, response["totalStake"])

        preps: list = response["preps"]
        self.assertEqual(prep_count, len(preps))
        for i in range(prep_count):
            stake: int = i * 10 * ICX_IN_LOOP
            prep: dict = preps[i]
            self.assertEqual(stake, prep["stake"])

        # Change the stake of each P-Rep
        total_stake = 0
        stake: int = 10 * ICX_IN_LOOP
        tx_list = []
        for account in accounts:
            total_stake += stake

            tx = self.create_set_stake_tx(from_=account,
                                          value=stake)
            tx_list.append(tx)

        self.process_confirm_block_tx(tx_list)

        # setStake with user_address
        stake = 50 * ICX_IN_LOOP
        tx_list = [self.create_set_stake_tx(from_=user_account,
                                            value=stake)]

        self.process_confirm_block_tx(tx_list)
        total_stake += stake

        # Check the stakes of P-Reps
        response: dict = self.get_prep_list(start_ranking=1)
        # total_stake means the sum of stakes which all addresses have
        self.assertEqual(total_stake, response["totalStake"])

        preps: list = response["preps"]
        self.assertEqual(prep_count, len(preps))

        for i in range(prep_count):
            prep: dict = preps[i]
            self.assertEqual(10 * ICX_IN_LOOP, prep["stake"])

            prep: dict = self.get_prep(prep["address"])
            self.assertEqual(10 * ICX_IN_LOOP, prep["stake"])

    def test_prep_query_via_icx_sendtransaction(self):
        self.init_decentralized(clear=False)
        query = {
            PRepMethod.GET_PREP: {"address": str(self._accounts[0].address)},
            PRepMethod.GET_MAIN_PREPS: {},
            PRepMethod.GET_SUB_PREPS: {},
            PRepMethod.GET_PREPS: {"startRanking": "0x1", "endRanking": "0x2"},
            PRepMethod.GET_PREP_TERM: {},
            PRepMethod.GET_INACTIVE_PREPS: {},
        }

        # TEST : query via icx_sendTransaction (revision < ALLOW_INVOKE_SYSTEM_SCORE_READONLY)
        for method, param in query.items():
            self.check_query_via_icx_sendtransaction(method, param, False)

        # TEST : query via icx_sendTransaction (revision >= ALLOW_INVOKE_SYSTEM_SCORE_READONLY)
        self.set_revision(Revision.SYSTEM_SCORE_ENABLED.value, with_np=True)
        for method, param in query.items():
            self.check_query_via_icx_sendtransaction(method, param, True)
        return

    def check_query_via_icx_sendtransaction(self, method: str, params: dict, expected_status: bool):
        tx = self.create_score_call_tx(from_=self._admin,
                                       to_=SYSTEM_SCORE_ADDRESS,
                                       func_name=method,
                                       params=params)
        return self.process_confirm_block_tx([tx], expected_status=expected_status)

    def test_get_preps_normal(self):
        self.init_decentralized()

        start_ranking = 1
        end_ranking = 10

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }
        ret = self._query(query_request)
        self.assertEqual(start_ranking, ret["startRanking"])
        self.assertEqual(end_ranking, len(ret["preps"]))

    def test_get_preps_over_start_ranking(self):
        self.init_decentralized()

        start_ranking = 10_000
        end_ranking = 10_000 + 1

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }
        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking({start_ranking}), endRanking({end_ranking})")

    def test_get_preps_over_end_ranking(self):
        self.init_decentralized()

        start_ranking = 1
        end_ranking = 10_000
        expected_prep_count = 22

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }
        ret = self._query(query_request)
        self.assertEqual(start_ranking, ret["startRanking"])
        self.assertEqual(expected_prep_count, len(ret["preps"]))

    def test_get_preps_raise_start_zero(self):
        self.init_decentralized()

        start_ranking = 0
        end_ranking = 10

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking({start_ranking}), endRanking({end_ranking})")

    def test_get_preps_raise_end_zero(self):
        self.init_decentralized()

        end_ranking = 0

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "endRanking": hex(end_ranking),
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking(None), endRanking({end_ranking})")

    def test_get_preps_raise_reverse(self):
        self.init_decentralized()

        start_ranking = 10
        end_ranking = 2

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking({start_ranking}), endRanking({end_ranking})")

    def test_get_preps_raise_only_one(self):
        self.init_decentralized()

        start_ranking = 10
        end_ranking = 10

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                    "endRanking": hex(end_ranking),
                }
            }
        }

        ret = self._query(query_request)
        self.assertEqual(start_ranking, ret["startRanking"])
        self.assertEqual(1, len(ret["preps"]))

    def test_get_preps_negative_start(self):
        self.init_decentralized()

        start_ranking = -10
        expected_prep_count = 22

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "startRanking": hex(start_ranking),
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking({start_ranking}), endRanking(None)")

    def test_get_preps_negative_end(self):
        self.init_decentralized()

        end_ranking = -20

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": SYSTEM_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": PRepMethod.GET_PREPS,
                "params": {
                    "endRanking": hex(end_ranking),
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)

        self.assertEqual(e.exception.args[0], f"Invalid ranking: startRanking(None), endRanking({end_ranking})")
