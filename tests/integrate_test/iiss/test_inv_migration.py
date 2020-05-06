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
from random import randint
from typing import TYPE_CHECKING, Optional

from iconservice import IconNetworkValueType, Address
from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, AddressPrefix
from iconservice.icon_constant import (
    ConfigKey,
    Revision,
    IconScoreContextType,
    IconServiceFlag,
)
from iconservice.inv.container import ValueConverter, Container
from iconservice.inv.data.value import Value
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_step import StepType
from tests import create_address
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


# is: icon service, gs: governance score
class TestINVMigration(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()

    def _get_step_price(self):
        return self.query_score(
            from_=None, to_=GOVERNANCE_SCORE_ADDRESS, func_name="getStepPrice"
        )

    def _set_step_price(self, step_price: int, is_migrated: bool):
        func_name = "set_step_price" if is_migrated else "setStepPrice"
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name=func_name,
            params={"stepPrice": hex(step_price)},
            expected_status=True,
        )

    def _is_in_score_black_list(self, address: "Address"):
        return self.query_score(
            from_=None,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="isInScoreBlackList",
            params={"address": str(address)},
        )

    def _add_to_score_black_list(self, address: "Address", is_migrated: bool):
        func_name = "add_to_score_black_list" if is_migrated else "addToScoreBlackList"
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name=func_name,
            params={"address": str(address)},
            expected_status=True,
        )

    def _is_in_import_white_list(self, import_stmt: str):
        return self.query_score(
            from_=None,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="isInImportWhiteList",
            params={"importStmt": import_stmt},
        )

    def _add_import_white_list(self, import_stmt: str, is_migrated: bool):
        if is_migrated:
            return

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="addImportWhiteList",
            params={"importStmt": import_stmt},
            expected_status=True,
        )

    def _remove_import_white_list(self, import_stmt: str):
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="removeImportWhiteList",
            params={"importStmt": import_stmt},
            expected_status=True,
        )

    def _get_step_costs(self):
        return self.query_score(
            from_=None, to_=GOVERNANCE_SCORE_ADDRESS, func_name="getStepCosts"
        )

    def _set_step_costs(self, step_type: str, cost: int, is_migrated: bool):
        func_name = "set_step_cost" if is_migrated else "setStepCost"
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name=func_name,
            params={"stepType": step_type, "cost": hex(cost)},
            expected_status=True,
        )

    def _get_max_step_limit(self, context_type: str):
        return self.query_score(
            from_=None,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="getMaxStepLimit",
            params={"contextType": context_type},
        )

    def _set_max_step_limit(self, context_type: str, value: int, is_migrated: bool):
        func_name = "set_max_step_limit" if is_migrated else "setMaxStepLimit"
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name=func_name,
            params={"contextType": context_type, "value": hex(value)},
            expected_status=True,
        )

    def _get_revision(self):
        return self.query_score(
            from_=None, to_=GOVERNANCE_SCORE_ADDRESS, func_name="getRevision"
        )

    # Override
    def _set_revision(self, revision: int, is_migrated: bool):
        func_name = "set_revision" if is_migrated else "setRevision"
        return self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name=func_name,
            params={"code": hex(revision), "name": f"1.1.{revision}"},
            expected_status=True,
        )

    def _get_service_config(self):
        return self.query_score(
            from_=None, to_=GOVERNANCE_SCORE_ADDRESS, func_name="getServiceConfig"
        )

    def _get_version(self):
        return self.query_score(
            from_=None, to_=GOVERNANCE_SCORE_ADDRESS, func_name="getVersion"
        )

    def _get_inv_from_is(self, inv_type: "IconNetworkValueType"):
        inv_container: "Container" = IconScoreContext.engine.inv.inv_container
        return inv_container.get_by_type(inv_type)

    def _get_is_migrated_from_is(self):
        inv_container: "Container" = IconScoreContext.engine.inv.inv_container
        return inv_container.is_migrated

    def _convert_service_config_from_int_to_dict(self, service_flag: int) -> dict:
        is_service_config: dict = {}
        for flag in IconServiceFlag:
            if service_flag & flag == flag:
                is_service_config[flag.name] = True
            else:
                is_service_config[flag.name] = False
        return is_service_config

    def check_inv(self, is_migrated):
        # Actual test code

        """Service Config"""
        # TEST: service config should be same between icon-service and governance
        gs_service_config: dict = self._get_service_config()
        is_service_flag: int = self._get_inv_from_is(
            IconNetworkValueType.SERVICE_CONFIG
        )
        is_service_config: dict = self._convert_service_config_from_int_to_dict(
            is_service_flag
        )
        assert gs_service_config == is_service_config

        """Step Price"""
        # TEST: Step price should be same between icon-service and governance
        gs_step_price: int = self._get_step_price()
        is_step_price = self._get_inv_from_is(IconNetworkValueType.STEP_PRICE)

        assert is_step_price == gs_step_price

        # TEST: When update the step price, icon service should update accordingly
        expected_step_price: int = randint(10, 20)

        self._set_step_price(expected_step_price, is_migrated)
        gs_step_price: int = self._get_step_price()
        is_step_price = self._get_inv_from_is(IconNetworkValueType.STEP_PRICE)

        assert is_step_price == gs_step_price == expected_step_price

        """Step Costs"""
        # TEST: Step costs should be same between icon-service and governance
        gs_step_costs = self._get_step_costs()
        is_step_costs = ValueConverter.convert_for_governance(
            IconNetworkValueType.STEP_COSTS,
            self._get_inv_from_is(IconNetworkValueType.STEP_COSTS),
        )

        assert is_step_costs == gs_step_costs

        # TEST: When update the step costs, icon service should update accordingly
        for step_type in StepType:
            type_: str = step_type.value
            expected_costs = randint(10, 100)

            self._set_step_costs(type_, expected_costs, is_migrated=is_migrated)

            gs_step_costs = self._get_step_costs()
            is_step_costs = self._get_inv_from_is(IconNetworkValueType.STEP_COSTS)

            assert (
                gs_step_costs[type_] == is_step_costs[StepType(type_)] == expected_costs
            )

        """Max Step Limits"""
        # TEST: Max step limits should be same between icon-service and governance
        gs_invoke_max_step_limit = self._get_max_step_limit("invoke")
        gs_query_max_step_limit = self._get_max_step_limit("query")
        is_max_step_limit = self._get_inv_from_is(IconNetworkValueType.MAX_STEP_LIMITS)

        assert (
            is_max_step_limit[IconScoreContextType.INVOKE] == gs_invoke_max_step_limit
        )
        assert is_max_step_limit[IconScoreContextType.QUERY] == gs_query_max_step_limit

        # TEST: When update the max step limits, icon service should update accordingly
        invoke_type: str = "invoke"
        query_type: str = "query"
        expected_invoke_value = randint(2_600_000_000, 2_700_000_000)
        expected_query_value = randint(60_000_000, 70_000_000)

        self._set_max_step_limit(invoke_type, expected_invoke_value, is_migrated)
        self._set_max_step_limit(query_type, expected_query_value, is_migrated)

        gs_invoke_max_step_limit = self._get_max_step_limit("invoke")
        gs_query_max_step_limit = self._get_max_step_limit("query")
        is_max_step_limit = self._get_inv_from_is(IconNetworkValueType.MAX_STEP_LIMITS)

        assert (
            is_max_step_limit[IconScoreContextType.INVOKE]
            == gs_invoke_max_step_limit
            == expected_invoke_value
        )
        assert (
            is_max_step_limit[IconScoreContextType.QUERY]
            == gs_query_max_step_limit
            == expected_query_value
        )

        """Revision"""
        # TEST: Revision should be same between icon-service and governance
        gs_revision = self._get_revision()
        is_revision_code = self._get_inv_from_is(IconNetworkValueType.REVISION_CODE)
        is_revision_name = self._get_inv_from_is(IconNetworkValueType.REVISION_NAME)

        assert is_revision_code == gs_revision["code"]
        assert is_revision_name == gs_revision["name"]

        # TEST: When update the revision, icon service should update accordingly
        expected_revision_value = Revision.IISS.value
        expected_revision_name = f"1.1.{Revision.IISS.value}"

        self._set_revision(expected_revision_value, is_migrated)

        gs_revision = self._get_revision()
        is_revision_code = self._get_inv_from_is(IconNetworkValueType.REVISION_CODE)
        is_revision_name = self._get_inv_from_is(IconNetworkValueType.REVISION_NAME)

        assert is_revision_code == gs_revision["code"] == expected_revision_value
        assert is_revision_name == gs_revision["name"] == expected_revision_name

        """Score Black List"""
        # TEST: Score black list should be same between icon-service and governance
        expected_is_in_black_list: bool = False
        score_address: "Address" = create_address(AddressPrefix.CONTRACT)

        gs_is_in_black_list = self._is_in_score_black_list(score_address)
        is_is_in_black_list = score_address in self._get_inv_from_is(
            IconNetworkValueType.SCORE_BLACK_LIST
        )

        assert is_is_in_black_list == gs_is_in_black_list == expected_is_in_black_list

        # TEST: When update the Score black list, icon service should update accordingly
        expected_is_in_black_list: bool = True

        self._add_to_score_black_list(score_address, is_migrated)
        gs_is_in_black_list = self._is_in_score_black_list(score_address)
        is_is_in_black_list = score_address in self._get_inv_from_is(
            IconNetworkValueType.SCORE_BLACK_LIST
        )

        assert is_is_in_black_list == gs_is_in_black_list == expected_is_in_black_list

        """Import White List"""
        # TEST: Import white list should be same between icon-service and governance
        expected_is_in_import_list: bool = False
        import_stmt = "{'os': ['path']}"
        is_import_list = self._get_inv_from_is(IconNetworkValueType.IMPORT_WHITE_LIST)

        gs_is_in_import_list = self._is_in_import_white_list(import_stmt)
        is_is_in_import_list = is_import_list.get("os", None) is not None

        assert (
            is_is_in_import_list == gs_is_in_import_list == expected_is_in_import_list
        )

        # TEST: When add import white list, icon service should update accordingly
        # After governance 0.0.6, adding import white list is removed. So do not test after migration
        if not is_migrated:
            expected_is_in_import_list: bool = True

            self._add_import_white_list(import_stmt, is_migrated)
            gs_is_in_import_list = self._is_in_import_white_list(import_stmt)
            is_is_in_import_list = (
                self._get_inv_from_is(IconNetworkValueType.IMPORT_WHITE_LIST).get(
                    "os", None
                )
                is not None
            )

            assert (
                is_is_in_import_list
                == gs_is_in_import_list
                == expected_is_in_import_list
            )

            # Remove added import white list (kind of tear down)
            self._remove_import_white_list(import_stmt)

    def _inv_is_stored_on_state_db(self) -> bool:
        context: "IconScoreContext" = IconScoreContext()
        for type_ in IconNetworkValueType:
            inv_value: Optional["Value"] = IconScoreContext.storage.inv._get_value(
                context, type_
            )
            if inv_value is None:
                return False
        return True

    def _is_migration_flag_stored_on_state_db(self) -> bool:
        context: "IconScoreContext" = IconScoreContext()
        return IconScoreContext.storage.inv._get_migration_flag(context)

    def test_before_migration(self):
        self.update_governance(version="0_0_6")
        self.check_inv(is_migrated=False)

        assert self._inv_is_stored_on_state_db() is False
        assert self._is_migration_flag_stored_on_state_db() is False

    def test_after_migration(self):
        self.update_governance(
            version="1_0_1", expected_status=True, root_path="sample_builtin_for_tests"
        )
        self.check_inv(is_migrated=True)

        assert self._inv_is_stored_on_state_db() is True
        assert self._is_migration_flag_stored_on_state_db() is True

    def test_before_and_after_migration(self):
        # TEST: When before upgrade GS to version 1.0.1, all INVs should be same between icon-service and governance
        # and all INVs must not be stored on stateDB
        self.update_governance(version="0_0_6")
        self.check_inv(is_migrated=False)

        assert self._inv_is_stored_on_state_db() is False
        assert self._is_migration_flag_stored_on_state_db() is False

        # TEST: When After upgrade GS to version 1.0.1, all INVs should be same between icon-service and governance
        # and all INVs must be stored on stateDB
        self.update_governance(
            version="1_0_1", expected_status=True, root_path="sample_builtin_for_tests"
        )
        self.check_inv(is_migrated=True)

        assert self._inv_is_stored_on_state_db() is True
        assert self._is_migration_flag_stored_on_state_db() is True

    # FIXME: use fixture.marks.parameterize
    def test_when_put_insufficient_invs_on_migration_should_rollback_to_before_migration(
        self,
    ):
        # TEST: Test case about raising exception during migration
        expected_status: bool = False
        self.update_governance(version="0_0_6")

        # Act
        self.update_governance(
            version="1_0_1_insufficient_invs",
            expected_status=expected_status,
            root_path="sample_builtin_for_tests",
        )

        assert self._get_is_migrated_from_is() is False
        assert self._inv_is_stored_on_state_db() is False
        assert self._is_migration_flag_stored_on_state_db() is False
        assert self._get_version() == "0.0.6"

        # TEST: After fail to update governance, INVs related logic should be worked
        self.check_inv(False)

    def test_when_revert_during_update_should_rollback_to_before_migration(self):
        # TEST: Test case about raising exception during migration
        expected_status: bool = False
        self.update_governance(version="0_0_6")

        # Act
        self.update_governance(
            version="1_0_1_revert_on_update",
            expected_status=expected_status,
            root_path="sample_builtin_for_tests",
        )

        assert self._get_is_migrated_from_is() is False
        assert self._inv_is_stored_on_state_db() is False
        assert self._is_migration_flag_stored_on_state_db() is False
        assert self._get_version() == "0.0.6"

        # TEST: After fail to update governance, INVs related logic should be worked
        self.check_inv(False)

    def test_when_revert_end_of_updating_should_rollback_to_before_migration(self):
        # TEST: Test case about raising exception during migration
        expected_status: bool = False
        self.update_governance(version="0_0_6")

        # Act
        self.update_governance(
            version="1_0_1_revert_at_the_end_of_update",
            expected_status=expected_status,
            root_path="sample_builtin_for_tests",
        )

        assert self._get_is_migrated_from_is() is False
        assert self._inv_is_stored_on_state_db() is False
        assert self._is_migration_flag_stored_on_state_db() is False
        assert self._get_version() == "0.0.6"

        # TEST: After fail to update governance, INVs related logic should be worked
        self.check_inv(False)

    def test_when_change_the_invs_while_migration_should_be_succeed(self):
        # TEST: Test case about migration success
        expected_status: bool = True
        self.update_governance(version="0_0_6")

        # Act
        self.update_governance(
            version="1_0_1_change_the_value_of_invs_on_migrations",
            expected_status=expected_status,
            root_path="sample_builtin_for_tests",
        )

        assert self._get_is_migrated_from_is() is True
        assert self._inv_is_stored_on_state_db() is True
        assert self._is_migration_flag_stored_on_state_db() is True
        assert self._get_version() == "1.0.1"

        # TEST: After success to update governance, INVs related logic should be worked
        self.check_inv(True)
