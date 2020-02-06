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

from iconservice.base.address import Address
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_INITIAL_IREP, PRepGrade, PRepStatus, PenaltyReason
from iconservice.icon_constant import Revision, PREP_MAIN_PREPS, ConfigKey, IISS_MAX_DELEGATIONS, ICX_IN_LOOP
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
                "txIndex": i
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
            "startRanking": 0,
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

        response: dict = self.get_prep_list(start_ranking=1)
        actual_preps: list = response['preps']
        self.assertEqual(prep_count, len(actual_preps))

    def test_preps_and_delegated(self):
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
        for i in range(IISS_MAX_DELEGATIONS):
            delegations.append((self._accounts[i], delegation_amount))
        self.set_delegation(from_=self._accounts[0],
                            origin_delegations=delegations)

        response: dict = self.get_main_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_sub_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_prep_list(end_ranking=IISS_MAX_DELEGATIONS)
        preps: list = []
        for i in range(IISS_MAX_DELEGATIONS):
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
                    "p2pEndpoint": expected_params["p2pEndpoint"]
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
        self.set_revision(Revision.IISS.value)

        # gain 10 icx user0
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:8],
                            init_balance=balance)

        self._validate_name()
        self._validate_email()
        self._validate_website()
        self._validate_country()
        self._validate_city()
        self._validate_details()
        self._validate_p2p_endpoint()

    def test_reg_prep_validator_fixed_email_validation(self):
        self.update_governance()

        # set Revision REV_FIX_EMAIL_REGEX
        self.set_revision(Revision.FIX_EMAIL_VALIDATION.value)

        # gain 10 icx user0
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:8],
                            init_balance=balance)

        self._validate_name()
        self._validate_fixed_email()
        self._validate_website()
        self._validate_country()
        self._validate_city()
        self._validate_details()
        self._validate_p2p_endpoint()

    def _validate_name(self):
        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.NAME] = ''
        tx = self.create_register_prep_tx(self._accounts[0], reg_data)
        self.process_confirm_block_tx([tx],
                                      expected_status=False)

        reg_data[ConstantKeys.NAME] = "valid name"
        tx = self.create_register_prep_tx(self._accounts[0], reg_data)
        self.process_confirm_block_tx([tx])

    def _validate_email(self):
        invalid_email_list = ['', 'invalid email', 'invalid.com', 'invalid@', 'invalid@a', 'invalid@a.',
                              'invalid@.com']

        for email in invalid_email_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.EMAIL] = email
            tx = self.create_register_prep_tx(self._accounts[1], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.EMAIL] = "valid@validexample.com"
        tx = self.create_register_prep_tx(self._accounts[1], reg_data)
        self.process_confirm_block_tx([tx])

    def _validate_fixed_email(self):
        invalid_email_list = ['invalid email', 'invalid.com', 'invalid@', f"{'a'*65}@example.com",
                              f"{'a'*253}@aa", '@invalid', f'{"가"*64}@example.com']

        for email in invalid_email_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.EMAIL] = email
            tx = self.create_register_prep_tx(self._accounts[1], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

        reg_data: dict = deepcopy(prep_register_data)
        chinese_mail = '你好@validexample.com'
        reg_data[ConstantKeys.EMAIL] = chinese_mail
        tx = self.create_register_prep_tx(self._accounts[1], reg_data)
        self.process_confirm_block_tx([tx])
        registered_data = self.get_prep(self._accounts[1])
        self.assertEqual(chinese_mail, registered_data['email'])

    def _validate_website(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.WEBSITE] = website
            tx = self.create_register_prep_tx(self._accounts[2], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.WEBSITE] = "https://validurl.com"
        tx = self.create_register_prep_tx(self._accounts[2], reg_data)
        self.process_confirm_block_tx([tx])

    # TODO
    def _validate_country(self):
        pass

    # TODO
    def _validate_city(self):
        pass

    def _validate_details(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.WEBSITE] = website
            tx = self.create_register_prep_tx(self._accounts[5], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.WEBSITE] = "https://validurl.com/json"
        tx = self.create_register_prep_tx(self._accounts[5], reg_data)
        self.process_confirm_block_tx([tx])

    def _validate_p2p_endpoint(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."
                                                                                    "https://target.asdf:7100"]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.P2P_ENDPOINT] = website
            tx = self.create_register_prep_tx(self._accounts[6], reg_data)
            self.process_confirm_block_tx([tx],
                                          expected_status=False)

        validate_endpoint = "20.20.7.8:8000"

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.P2P_ENDPOINT] = validate_endpoint
        tx = self.create_register_prep_tx(self._accounts[6], reg_data)
        self.process_confirm_block_tx([tx])

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
