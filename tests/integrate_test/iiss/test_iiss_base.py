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
from typing import TYPE_CHECKING, List, Tuple, Dict, Union, Optional

from iconservice.base.address import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import ConfigKey, REV_IISS, PREP_MAIN_PREPS, ICX_IN_LOOP, \
    REV_DECENTRALIZATION, PREP_MAIN_AND_SUB_PREPS
from tests.integrate_test.test_integrate_base import TestIntegrateBase, TOTAL_SUPPLY, DEFAULT_STEP_LIMIT

if TYPE_CHECKING:
    from tests.integrate_test.test_integrate_base import EOAAccount
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSBase(TestIntegrateBase):
    CALCULATE_PERIOD = 10
    TERM_PERIOD = 10

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_CALCULATE_PERIOD: self.CALCULATE_PERIOD,
            ConfigKey.TERM_PERIOD: self.TERM_PERIOD,
            ConfigKey.IISS_META_DATA: {
                ConfigKey.UN_STAKE_LOCK_MIN: 10,
                ConfigKey.UN_STAKE_LOCK_MAX: 20
            }
        }

    def make_blocks(self,
                    to: int,
                    prev_block_generator: Optional['Address'] = None,
                    prev_block_validators: Optional[List['Address']] = None,
                    prev_block_votes: Optional[List[List[Union['Address', bool]]]] = None)\
            -> List[List['TransactionResult']]:
        block_height = self._block_height
        tx_results: List[List['TransactionResult']] = []

        while to > block_height:
            tx = self.create_transfer_icx_tx(self._admin,
                                             self._genesis,
                                             0)
            tx_results.append(self.process_confirm_block_tx([tx],
                                                            prev_block_generator=prev_block_generator,
                                                            prev_block_validators=prev_block_validators,
                                                            prev_block_votes=prev_block_votes))
            block_height = self._block_height
        return tx_results

    def make_blocks_to_end_calculation(self,
                                       prev_block_generator: Optional['Address'] = None,
                                       prev_block_validators: Optional[List['Address']] = None,
                                       prev_block_votes: Optional[List[List[Union['Address', bool]]]] = None) -> int:
        iiss_info: dict = self.get_iiss_info()
        next_calculation: int = iiss_info.get('nextCalculation', 0)

        cur_block_height: int = self._block_height
        if cur_block_height == next_calculation - 1:
            # last calculate block
            self.make_blocks(to=next_calculation,
                             prev_block_generator=prev_block_generator,
                             prev_block_validators=prev_block_validators,
                             prev_block_votes=prev_block_votes)
            iiss_info: dict = self.get_iiss_info()
            next_calculation: int = iiss_info.get('nextCalculation', 0)

        self.make_blocks(to=next_calculation - 1,
                         prev_block_generator=prev_block_generator,
                         prev_block_validators=prev_block_validators,
                         prev_block_votes=prev_block_votes)

        self.assertEqual(self._block_height, next_calculation - 1)

        return next_calculation - 1

    def create_set_stake_tx(self,
                            from_: Union['EOAAccount', 'Address'],
                            value: int) -> dict:
        return self.create_score_call_tx(from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name="setStake",
                                         params={"value": hex(value)})

    def create_set_delegation_tx(self,
                                 from_: Union['EOAAccount', 'Address'],
                                 origin_delegations: List[Tuple[Union['EOAAccount', 'Address'], int]]) -> dict:
        delegations: List[Dict[str, str]] = self.create_delegation_params(origin_delegations)
        return self.create_score_call_tx(from_=from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name='setDelegation',
                                         params={"delegations": delegations})

    @classmethod
    def create_delegation_params(cls, params: List[Tuple[Union['EOAAccount', 'Address'], int]]) -> List[Dict[str, str]]:
        return [{"address": str(cls._convert_address_from_address_type(address)), "value": hex(value)}
                for (address, value) in params
                if value > 0]

    def create_register_prep_tx(self,
                                from_: 'EOAAccount',
                                reg_data: Dict[str, Union[str, bytes]] = None,
                                value: int = None) -> dict:

        if value is None:
            value: int = self._config[ConfigKey.PREP_REGISTRATION_FEE]
        if reg_data is None:
            reg_data: dict = self.create_register_prep_params(from_)

        return self.create_score_call_tx(from_=from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name="registerPRep",
                                         params=reg_data,
                                         value=value)

    @classmethod
    def create_register_prep_params(cls,
                                    from_: 'EOAAccount') -> Dict[str, str]:

        name = f"node{from_.address}"

        return {
            ConstantKeys.NAME: name,
            ConstantKeys.COUNTRY: "KOR",
            ConstantKeys.CITY: "Unknown",
            ConstantKeys.EMAIL: f"{name}@example.com",
            ConstantKeys.WEBSITE: f"https://{name}.example.com",
            ConstantKeys.DETAILS: f"https://{name}.example.com/details",
            ConstantKeys.P2P_ENDPOINT: f"{name}.example.com:7100",
        }

    def create_set_prep_tx(self,
                           from_: Union['EOAAccount', 'Address'],
                           set_data: Dict[str, Union[str, bytes]] = None) -> dict:
        if set_data is None:
            set_data: dict = {}
        return self.create_score_call_tx(from_=from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name="setPRep",
                                         params=set_data)

    def create_set_governance_variables(self,
                                        from_: Union['EOAAccount', 'Address'],
                                        irep: int) -> dict:
        """Create a setGovernanceVariables TX

        :param from_:
        :param irep: irep in loop
        :return:
        """
        return self.create_score_call_tx(
            from_=from_,
            to_=ZERO_SCORE_ADDRESS,
            func_name="setGovernanceVariables",
            params={"irep": hex(irep)}
        )

    def create_unregister_prep_tx(self,
                                  from_: 'EOAAccount') -> dict:
        return self.create_score_call_tx(from_=from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name="unregisterPRep",
                                         params={})

    def create_claim_tx(self,
                        from_: Union['EOAAccount', 'Address']) -> dict:
        return self.create_score_call_tx(from_=from_,
                                         to_=ZERO_SCORE_ADDRESS,
                                         func_name="claimIScore",
                                         params={})

    def get_main_prep_list(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getMainPReps",
                "params": {}
            }
        }
        return self._query(query_request)

    def get_sub_prep_list(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getSubPReps",
                "params": {}
            }
        }
        return self._query(query_request)

    def get_prep_list(self,
                      start_ranking: Optional[int] = None,
                      end_ranking: Optional[int] = None) -> dict:
        params = {}
        if start_ranking is not None:
            params['startRanking'] = hex(start_ranking)
        if end_ranking is not None:
            params['endRanking'] = hex(end_ranking)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPReps",
                "params": params
            }
        }
        return self._query(query_request)

    def get_p2p_endpoints(self):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getP2PEndpoints"
            }
        }
        return self._query(query_request)

    def get_prep(self,
                 from_: Union['EOAAccount', 'Address', str]) -> dict:
        address: Optional['Address'] = self._convert_address_from_address_type(from_)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {"address": str(address)}
            }
        }
        return self._query(query_request)

    def get_stake(self,
                  from_: Union['EOAAccount', 'Address', str]) -> dict:
        address: Optional['Address'] = self._convert_address_from_address_type(from_)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getStake",
                "params": {"address": str(address)}
            }
        }
        return self._query(query_request)

    def estimate_unstake_lock_period(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "estimateUnstakeLockPeriod"
            }

        }
        return self._query(query_request)

    def get_delegation(self,
                       from_: Union['EOAAccount', 'Address', str]) -> dict:
        address: Optional['Address'] = self._convert_address_from_address_type(from_)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getDelegation",
                "params": {"address": str(address)}
            }
        }
        return self._query(query_request)

    def query_iscore(self,
                     from_: Union['EOAAccount', 'Address', str]) -> dict:
        address: Optional['Address'] = self._convert_address_from_address_type(from_)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "queryIScore",
                "params": {"address": str(address)}
            }
        }
        return self._query(query_request)

    def get_iiss_info(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getIISSInfo",
                "params": {}
            }
        }
        return self._query(query_request)

    # ===== API =====#

    def claim_iscore(self,
                     from_: Union['EOAAccount', 'Address'],
                     expected_status: bool = True,
                     prev_block_generator: Optional['Address'] = None,
                     prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_claim_tx(from_=from_)
        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def set_stake(self,
                  from_: Union['EOAAccount', 'Address'],
                  value: int,
                  expected_status: bool = True,
                  prev_block_generator: Optional['Address'] = None,
                  prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_set_stake_tx(from_=from_,
                                            value=value)

        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def set_delegation(self,
                       from_: Union['EOAAccount', 'Address'],
                       origin_delegations: List[Tuple[Union['EOAAccount', 'Address'], int]],
                       expected_status: bool = True,
                       prev_block_generator: Optional['Address'] = None,
                       prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_set_delegation_tx(from_=from_,
                                                 origin_delegations=origin_delegations)
        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def register_prep(self,
                      from_: 'EOAAccount',
                      reg_data: Dict[str, Union[str, bytes]] = None,
                      value: int = None,
                      expected_status: bool = True,
                      prev_block_generator: Optional['Address'] = None,
                      prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_register_prep_tx(from_=from_,
                                                reg_data=reg_data,
                                                value=value)

        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def unregister_prep(self,
                        from_: 'EOAAccount',
                        expected_status: bool = True,
                        prev_block_generator: Optional['Address'] = None,
                        prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_unregister_prep_tx(from_=from_)

        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def set_governance_variables(self,
                                 from_: Union['EOAAccount', 'Address'],
                                 irep: int,
                                 expected_status: bool = True,
                                 prev_block_generator: Optional['Address'] = None,
                                 prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx: dict = self.create_set_governance_variables(from_=from_,
                                                        irep=irep)
        return self.process_confirm_block_tx([tx],
                                             expected_status=expected_status,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def distribute_icx(self,
                       accounts: List[Union['EOAAccount', 'Address']],
                       init_balance: int,
                       prev_block_generator: Optional['Address'] = None,
                       prev_block_validators: Optional[List['Address']] = None) -> List['TransactionResult']:
        tx_list: List[dict] = []
        for account in accounts:
            tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                                   to_=account,
                                                   value=init_balance)
            tx_list.append(tx)
        return self.process_confirm_block_tx(tx_list,
                                             prev_block_generator=prev_block_generator,
                                             prev_block_validators=prev_block_validators)

    def init_decentralized(self):
        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REV_IISS)

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 2

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=init_balance)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                value=stake_amount)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

        # register PRep
        tx_list: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                     origin_delegations=[
                                                         (
                                                             self._accounts[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_response: dict = {
            "preps": [],
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        # set Revision REV_IISS (decentralization)
        self.set_revision(REV_DECENTRALIZATION)

        self.make_blocks_to_end_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': minimum_delegate_amount_for_decentralization
            })
            expected_total_delegated += minimum_delegate_amount_for_decentralization
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        # delegate to PRep 0
        tx_list: list = []
        for account in self._accounts:
            tx: dict = self.create_set_delegation_tx(from_=account,
                                                     origin_delegations=[])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        self.make_blocks_to_end_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        max_expired_block_height: int = self._config[ConfigKey.IISS_META_DATA][ConfigKey.UN_STAKE_LOCK_MAX]
        self.make_blocks(self._block_height + max_expired_block_height + 1)

        tx_list: list = []
        for account in self._accounts:
            tx: dict = self.create_set_stake_tx(from_=account,
                                                value=0)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        tx_list: list = []
        step_price: int = self.get_step_price()
        fee: int = DEFAULT_STEP_LIMIT * step_price

        for account in self._accounts:
            balance: int = self.get_balance(account)

            if balance - fee > 0:
                tx: dict = self.create_transfer_icx_tx(from_=account,
                                                       to_=self._admin,
                                                       value=balance - fee)
                tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)
