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
from random import random, randint
from typing import TYPE_CHECKING

from iconservice import IconNetworkValueType, Address
from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, AddressPrefix
from iconservice.icon_constant import ConfigKey, Revision, IconScoreContextType
from iconservice.icon_network.container import ValueConverter, Container
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_step import StepType
from tests import create_address
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


# is: icon service, gs: governance score
class TestIconNetworkValue(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()

    def _get_step_price(self):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="getStepPrice")

    def _set_step_price(self, step_price: int, is_migrated: bool):
        func_name = "set_step_price" if is_migrated else "setStepPrice"
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name=func_name,
                        params={"stepPrice": hex(step_price)},
                        expected_status=True)

    def _is_in_score_black_list(self, address: 'Address'):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="isInScoreBlackList",
                                params={"address": str(address)})

    def _add_to_score_black_list(self, address: 'Address', is_migrated: bool):
        func_name = "add_to_score_black_list" if is_migrated else "addToScoreBlackList"
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name=func_name,
                        params={"address": str(address)},
                        expected_status=True)


    def _get_step_costs(self):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="getStepCosts")

    def _set_step_costs(self, step_type: str, cost: int, is_migrated: bool):
        func_name = "set_step_cost" if is_migrated else "setStepCost"
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name=func_name,
                        params={"stepType": step_type,
                                "cost": hex(cost)},
                        expected_status=True)

    def _get_max_step_limit(self, context_type: str):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="getMaxStepLimit",
                                params={
                                    "contextType": context_type
                                })

    def _set_max_step_limit(self, context_type: str, value: int, is_migrated: bool):
        func_name = "set_max_step_limit" if is_migrated else "setMaxStepLimit"
        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name=func_name,
                        params={"contextType": context_type,
                                "value": hex(value)},
                        expected_status=True)

    def _get_revision(self):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="getRevision")

    # Override
    def _set_revision(self, revision: int, is_migrated: bool):
        func_name = "set_revision" if is_migrated else "setRevision"
        return self.score_call(from_=self._admin,
                               to_=GOVERNANCE_SCORE_ADDRESS,
                               func_name=func_name,
                               params={"code": hex(revision), "name": f"1.1.{revision}"},
                               expected_status=True)

    def _get_service_config(self):
        return self.query_score(from_=None,
                                to_=GOVERNANCE_SCORE_ADDRESS,
                                func_name="getServiceConfig")

    def _get_inv_from_is(self, inv_type: 'IconNetworkValueType'):
        inv_container: 'Container' = IconScoreContext.engine.inv.inv_container
        return inv_container.get_by_type(inv_type)

    # Todo: do not write to DB before migration
    def check_inv(self, is_migrated):
        # Actual test code

        """Step Price"""
        # TEST: Step price should be same between icon-service and governance
        gs_step_price: int = self._get_step_price()
        is_step_price = self._get_inv_from_is(IconNetworkValueType.STEP_PRICE)

        assert is_step_price == gs_step_price

        # TEST: When update the step price, icon service should update accordingly
        expected_step_price: int = 10

        self._set_step_price(expected_step_price, is_migrated)
        gs_step_price: int = self._get_step_price()
        is_step_price = self._get_inv_from_is(IconNetworkValueType.STEP_PRICE)

        assert is_step_price == gs_step_price == expected_step_price

        """Step Costs"""
        # TEST: Step costs should be same between icon-service and governance
        gs_step_costs = self._get_step_costs()
        is_step_costs = ValueConverter.convert_for_governance_score(
            IconNetworkValueType.STEP_COSTS,
            self._get_inv_from_is(IconNetworkValueType.STEP_COSTS))

        assert is_step_costs == gs_step_costs

        # TEST: When update the step costs, icon service should update accordingly
        for step_type in StepType:
            type_: str = step_type.value
            expected_costs = randint(10, 100)

            self._set_step_costs(type_, expected_costs, is_migrated=is_migrated)

            gs_step_costs = self._get_step_costs()
            is_step_costs = self._get_inv_from_is(IconNetworkValueType.STEP_COSTS)

            assert gs_step_costs[type_] == is_step_costs[StepType(type_)] == expected_costs

        """Max Step Limits"""
        # TEST: Max step limits should be same between icon-service and governance
        gs_invoke_max_step_limit = self._get_max_step_limit("invoke")
        gs_query_max_step_limit = self._get_max_step_limit("query")
        is_max_step_limit = self._get_inv_from_is(IconNetworkValueType.MAX_STEP_LIMITS)

        assert is_max_step_limit[IconScoreContextType.INVOKE] == gs_invoke_max_step_limit
        assert is_max_step_limit[IconScoreContextType.QUERY] == gs_query_max_step_limit

        # TEST: When update the max step limits, icon service should update accordingly
        invoke_type: str = "invoke"
        query_type: str = "query"
        expected_invoke_value = 2_600_000_000
        expected_query_value = 60_000_000

        self._set_max_step_limit(invoke_type, expected_invoke_value, is_migrated)
        self._set_max_step_limit(query_type, expected_query_value, is_migrated)

        gs_invoke_max_step_limit = self._get_max_step_limit("invoke")
        gs_query_max_step_limit = self._get_max_step_limit("query")
        is_max_step_limit = self._get_inv_from_is(IconNetworkValueType.MAX_STEP_LIMITS)

        assert is_max_step_limit[IconScoreContextType.INVOKE] == gs_invoke_max_step_limit == expected_invoke_value
        assert is_max_step_limit[IconScoreContextType.QUERY] == gs_query_max_step_limit == expected_query_value

        """Revision"""
        # TEST: Revision should be same between icon-service and governance
        gs_revision = self._get_revision()
        is_revision_code = self._get_inv_from_is(IconNetworkValueType.REVISION_CODE)
        is_revision_name = self._get_inv_from_is(IconNetworkValueType.REVISION_NAME)

        assert is_revision_code == gs_revision['code']
        if is_migrated:
            assert is_revision_name == gs_revision['name']

        # TEST: When update the revision, icon service should update accordingly
        expected_revision_value = Revision.IISS.value
        expected_revision_name = f"1.1.{Revision.IISS.value}"

        self._set_revision(expected_revision_value, is_migrated)

        gs_revision = self._get_revision()
        is_revision_code = self._get_inv_from_is(IconNetworkValueType.REVISION_CODE)
        is_revision_name = self._get_inv_from_is(IconNetworkValueType.REVISION_NAME)

        assert is_revision_code == gs_revision['code'] == expected_revision_value
        if is_migrated:
            assert is_revision_name == gs_revision['name'] == expected_revision_name

        """Score Black List"""
        # TEST: Score black list should be same between icon-service and governance
        expected_boolean: bool = False
        dummy_score_address: 'Address' = create_address(AddressPrefix.CONTRACT)

        gs_is_in_black_list = self._is_in_score_black_list(dummy_score_address)
        is_is_in_black_list = dummy_score_address in self._get_inv_from_is(IconNetworkValueType.SCORE_BLACK_LIST)

        assert is_is_in_black_list == gs_is_in_black_list == expected_boolean

        # TEST: When update the Score black list, icon service should update accordingly
        expected_boolean: bool = True

        self._add_to_score_black_list(dummy_score_address, is_migrated)
        gs_is_in_black_list = self._is_in_score_black_list(dummy_score_address)
        is_is_in_black_list = dummy_score_address in self._get_inv_from_is(IconNetworkValueType.SCORE_BLACK_LIST)

        assert is_is_in_black_list == gs_is_in_black_list == expected_boolean

        """Import White List"""

        # # TEST: When service config should be same between icon-service and governance
        # gs_service_config = self._get_service_config()
        # is_service_config = self._get_inv_from_is(IconNetworkValueType.SERVICE_CONFIG)
        #
        # assert gs_service_config == is_service_config

    def test_before_migration(self):
        # Todo: Do not update using latest gs
        self.update_governance()
        self.check_inv(is_migrated=False)

    def test_after_migration(self):
        self.update_governance(version="1_0_1", expected_status=True, root_path="sample_builtin_for_tests")
        self.check_inv(is_migrated=True)
