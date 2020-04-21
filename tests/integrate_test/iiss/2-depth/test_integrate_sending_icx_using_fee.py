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

import json
from typing import TYPE_CHECKING, Optional

import pytest

from iconservice.base.address import Address
from iconservice.icon_constant import ConfigKey
from iconservice.icon_constant import Revision
from iconservice.utils import icx_to_loop
from tests import create_address, create_block_hash
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.icon_service_engine import IconServiceEngine


class TestIntegrateSendingIcx(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_FEE: True}}

    # def test_fail_icx_validator(self):
    #     icx = 3 * FIXED_FEE
    #     self.transfer_icx(from_=self._admin,
    #                       to_=self._accounts[0],
    #                       value=icx)
    #
    #     self.assertEqual(icx, self.get_balance(self._accounts[0]))
    #
    #     tx1 = self.create_transfer_icx_tx(from_=self._accounts[0],
    #                                       to_=self._accounts[1],
    #                                       value=1 * FIXED_FEE,
    #                                       support_v2=True)
    #     tx2 = self.create_transfer_icx_tx(from_=self._accounts[0],
    #                                       to_=self._accounts[1],
    #                                       value=1 * FIXED_FEE,
    #                                       support_v2=True)
    #     tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
    #
    #     self.assertEqual(tx_results[0].step_used, 1_000_000)
    #     # wrong!
    #     self.assertEqual(tx_results[1].step_used, 0)

    # def test_fix_icx_validator(self):
    #     self.update_governance()
    #     self.set_revision(Revision.THREE.value)
    #
    #     icx = 3 * FIXED_FEE
    #     self.transfer_icx(from_=self._admin,
    #                       to_=self._accounts[0],
    #                       value=icx)
    #
    #     self.assertEqual(icx, self.get_balance(self._accounts[0]))
    #
    #     tx1 = self.create_transfer_icx_tx(from_=self._accounts[0],
    #                                       to_=self._accounts[1],
    #                                       value=1 * FIXED_FEE,
    #                                       support_v2=True)
    #     tx2 = self.create_transfer_icx_tx(from_=self._accounts[0],
    #                                       to_=self._accounts[1],
    #                                       value=1 * FIXED_FEE,
    #                                       support_v2=True)
    #
    #     prev_block, hash_list = self.make_and_req_block([tx1, tx2])
    #     self._write_precommit_state(prev_block)
    #
    #     tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
    #     self.assertEqual(tx_results[0].step_used, 1_000_000)
    #     self.assertEqual(tx_results[1].status, 0)

    @staticmethod
    def _calculate_step_limit(
            revision: int,
            data: Optional[str] = None,
            default_step_cost: int = 100_000,
            input_step_cost: int = 200
    ) -> int:
        if revision == Revision.THREE.value:
            # Check backward compatibility on TestNet Database
            # step_used increases by input_step_cost * len(json.dumps(None))
            # because of None parameter handling error on get_input_data_size()
            step_limit = default_step_cost + input_step_cost * len(json.dumps(data))
        else:
            step_limit = default_step_cost

        return step_limit

    def test_send_icx(self):
        from_: 'Address' = self._admin.address
        step_price = 10 ** 10
        default_step_cost = 100_000
        input_step_cost = 200
        value = icx_to_loop(7)

        icon_service_engine: IconServiceEngine = self.icon_service_engine

        self.update_governance()

        for revision in range(Revision.THREE.value, Revision.LATEST.value + 1):
            self.set_revision(revision)

            # The latest confirmed block
            root_block = icon_service_engine._precommit_data_manager.last_block

            # Check that "from_" address has enough icx to transfer
            balance0: int = self.get_balance(from_)
            self.assertTrue(balance0 > value)

            # Check "to" address balance. It should be 0
            addresses = []
            for _ in range(2):
                address: 'Address' = create_address()
                balance: int = self.get_balance(address)
                assert balance == 0

                addresses.append(address)

            # Estimate the step limit of icx transfer tx
            step_limit = self._calculate_step_limit(
                revision,
                data=None,
                default_step_cost=default_step_cost,
                input_step_cost=input_step_cost
            )

            # Root -> Parent ========================================
            # from_ sends 10 ICX to addresses[0]
            tx = self.create_transfer_icx_tx(
                from_=from_,
                to_=addresses[0],
                value=value,
                disable_pre_validate=False,
                support_v2=False,
                step_limit=step_limit
            )

            prev_block = root_block
            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=prev_block)
            assert block.prev_hash == prev_block.hash
            assert block.height == prev_block.height + 1
            parent_block = block

            # Before confirming a parent block
            for address in addresses:
                balance = self.get_balance(address)
                assert balance == 0

            # Root -> Parent -> Child =====================================
            prev_block = block

            # addresses[0] sends 5 ICX to addresses[1]
            tx = self.create_transfer_icx_tx(
                from_=addresses[0],
                to_=addresses[1],
                value=icx_to_loop(5),
                disable_pre_validate=True,
                support_v2=False,
                step_limit=step_limit
            )

            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=prev_block)
            assert block.prev_hash == prev_block.hash
            assert block.height == prev_block.height + 1
            child_block = block

            # Before confirming a parent block
            for address in addresses:
                balance = self.get_balance(address)
                assert balance == 0

            self._write_precommit_state(parent_block)

            balance = self.get_balance(addresses[0])
            assert balance == icx_to_loop(7)

            balance = self.get_balance(addresses[1])
            assert balance == 0

            self._write_precommit_state(child_block)

            balance = self.get_balance(addresses[0])
            assert balance < icx_to_loop(5)

            balance = self.get_balance(addresses[1])
            assert balance == icx_to_loop(5)

    def test_send_icx2(self):
        from_: 'Address' = self._admin.address
        default_step_cost = 100_000
        input_step_cost = 200
        step_price = 10 ** 10
        revision = Revision.LATEST.value

        icon_service_engine: IconServiceEngine = self.icon_service_engine
        precommit_data_manager = icon_service_engine._precommit_data_manager

        self.update_governance()
        self.set_revision(Revision.LATEST.value)

        # Estimate the step limit of icx transfer tx
        step_limit = self._calculate_step_limit(
            revision,
            data=None,
            default_step_cost=default_step_cost,
            input_step_cost=input_step_cost
        )

        # The latest confirmed block
        root_block = icon_service_engine._precommit_data_manager.last_block

        # Check that "from_" address has enough icx to transfer
        from_balance: int = self.get_balance(from_)
        self.assertTrue(from_balance > 0)

        # Prepare empty addresses
        count = 3

        parent_addresses = []
        child_addresses = []
        for _ in range(count):
            address: 'Address' = create_address()
            balance: int = self.get_balance(address)
            assert balance == 0
            parent_addresses.append(address)

            address: 'Address' = create_address()
            balance: int = self.get_balance(address)
            assert balance == 0
            child_addresses.append(address)

        parent_blocks = []
        child_blocks = []

        # from_ sends 10 ICX to addresses[0]
        for i in range(count):
            balance = self.get_balance(from_)
            assert balance == from_balance

            value = icx_to_loop(1)

            # Root -> Parent ========================================
            tx = self.create_transfer_icx_tx(
                from_=from_,
                to_=parent_addresses[i],
                value=value,
                disable_pre_validate=False,
                support_v2=False,
                step_limit=step_limit
            )

            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=root_block)
            parent_blocks.append(block)

            # Root -> Parent -> Child =====================================
            value //= 2
            tx = self.create_transfer_icx_tx(
                from_=parent_addresses[i],
                to_=child_addresses[i],
                value=value,
                disable_pre_validate=True,
                support_v2=False,
                step_limit=step_limit
            )

            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=block)
            child_blocks.append(block)

        index = 0
        block = parent_blocks[index]
        self._write_precommit_state(block)

        for i in range(count):
            balance = self.get_balance(parent_addresses[i])
            assert balance == (icx_to_loop(1) if i == index else 0)
            assert self.get_balance(child_addresses[i]) == 0

            if i == index:
                assert precommit_data_manager.get(parent_blocks[i].hash)
                assert precommit_data_manager.get(child_blocks[i].hash)
            else:
                assert precommit_data_manager.get(parent_blocks[i].hash) is None
                assert precommit_data_manager.get(child_blocks[i].hash) is None

        last_block: 'Block' = precommit_data_manager.last_block
        parent_blocks[index].cumulative_fee = step_limit * step_price
        assert len(precommit_data_manager) == 2
        assert last_block == parent_blocks[index]

    def test_send_icx3(self):
        from_: 'Address' = self._admin.address
        step_price = 10 ** 10
        default_step_cost = 100_000
        input_step_cost = 200
        value = icx_to_loop(7)

        icon_service_engine: IconServiceEngine = self.icon_service_engine

        self.update_governance()

        for revision in range(Revision.THREE.value, Revision.LATEST.value + 1):
            self.set_revision(revision)

            # The latest confirmed block
            root_block = icon_service_engine._precommit_data_manager.last_block

            # Check that "from_" address has enough icx to transfer
            balance0: int = self.get_balance(from_)
            self.assertTrue(balance0 > value)

            # Check "to" address balance. It should be 0
            addresses = []
            for _ in range(2):
                address: 'Address' = create_address()
                balance: int = self.get_balance(address)
                assert balance == 0

                addresses.append(address)

            # Estimate the step limit of icx transfer tx
            step_limit = self._calculate_step_limit(
                revision,
                data=None,
                default_step_cost=default_step_cost,
                input_step_cost=input_step_cost
            )

            # Root -> Parent ========================================
            # from_ sends 10 ICX to addresses[0]
            tx = self.create_transfer_icx_tx(
                from_=from_,
                to_=addresses[0],
                value=value,
                disable_pre_validate=False,
                support_v2=False,
                step_limit=step_limit
            )

            prev_block = root_block
            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=prev_block)
            new_hash: bytes = create_block_hash()
            self._change_block_hash(block.height, block.hash, new_hash)
            block._hash = new_hash
            assert block.prev_hash == prev_block.hash
            assert block.height == prev_block.height + 1
            parent_block = block

            # Before confirming a parent block
            for address in addresses:
                balance = self.get_balance(address)
                assert balance == 0

            # Root -> Parent -> Child =====================================
            prev_block = block

            # addresses[0] sends 5 ICX to addresses[1]
            tx = self.create_transfer_icx_tx(
                from_=addresses[0],
                to_=addresses[1],
                value=icx_to_loop(5),
                disable_pre_validate=True,
                support_v2=False,
                step_limit=step_limit
            )

            block, hash_list = self.make_and_req_block_for_2_depth_invocation([tx], prev_block=prev_block)
            new_hash: bytes = create_block_hash()
            self._change_block_hash(block.height, block.hash, new_hash)
            block._hash = new_hash
            assert block.prev_hash == prev_block.hash
            assert block.height == prev_block.height + 1
            child_block = block

            # Before confirming a parent block
            for address in addresses:
                balance = self.get_balance(address)
                assert balance == 0

            self._write_precommit_state(parent_block)

            balance = self.get_balance(addresses[0])
            assert balance == icx_to_loop(7)

            balance = self.get_balance(addresses[1])
            assert balance == 0

            self._write_precommit_state(child_block)

            balance = self.get_balance(addresses[0])
            assert balance < icx_to_loop(5)

            balance = self.get_balance(addresses[1])
            assert balance == icx_to_loop(5)