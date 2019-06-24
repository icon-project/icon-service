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
from copy import deepcopy
from typing import Optional, List
from unittest.mock import patch

from iconservice.base.address import Address, GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import REV_DECENTRALIZATION, REV_IISS, \
    IconScoreContextType, IISS_MIN_IREP, PREP_MAIN_PREPS
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_address, create_block_hash
from tests.integrate_test import create_timestamp
from tests.integrate_test.test_integrate_base import TestIntegrateBase, LATEST_GOVERNANCE


class TestIntegrateDecentralization(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  LATEST_GOVERNANCE,
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results, main_prep_list = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def setUp(self):
        super().setUp()
        self._addr_array = [create_address() for _ in range(30)]
        self._update_governance()
        self._main_preps = self._addr_array[:22]
        self._set_revision(REV_IISS)

    def _make_and_req_block(self, tx_list: list,
                            block_height: int = None,
                            prev_block_generator: Optional['Address'] = None,
                            prev_block_validators: Optional[List['Address']] = None) -> tuple:
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash)
        context = IconScoreContext(IconScoreContextType.DIRECT)

        is_block_editable = False
        governance_score = self.icon_service_engine._get_governance_score(context)
        if hasattr(governance_score, 'revision_code') and governance_score.revision_code >= REV_IISS:
            is_block_editable = True

        invoke_response, _, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            is_block_editable=is_block_editable)

        return block, invoke_response, main_prep_as_dict

    def _set_revision(self, revision):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                   {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results, _ = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _stake_tx(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})
        return tx

    def _delegate_tx(self, address: 'Address', delegations: list):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})
        return tx

    def _reg_prep_tx(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value: str = data[ConstantKeys.PUBLIC_KEY].hex()
        data[ConstantKeys.PUBLIC_KEY] = value
        value: str = hex(data[ConstantKeys.IREP])
        data[ConstantKeys.IREP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
        return tx

    @patch('iconservice.iiss.get_minimum_delegate_for_bottom_prep')
    def test_decentralization_trigger(self, get_minimum_delegate):
        _MINIMUM_DELEGATE = 10**18
        _TERM = 10
        get_minimum_delegate.return_value = _MINIMUM_DELEGATE
        # distribute icx
        minimum_delegate = _MINIMUM_DELEGATE
        balance: int = minimum_delegate * 10
        tx1 = self._make_icx_send_tx(self._genesis, self._addr_array[22], balance)
        tx2 = self._make_icx_send_tx(self._genesis, self._addr_array[23], balance)
        tx3 = self._make_icx_send_tx(self._genesis, self._addr_array[24], balance)
        prev_block, tx_results, main_prep_list = self._make_and_req_block([tx1, tx2, tx3])
        self.assertIsNone(main_prep_list)
        self._write_precommit_state(prev_block)

        # stake
        stake_tx1 = self._stake_tx(self._addr_array[22], minimum_delegate * 10)
        stake_tx2 = self._stake_tx(self._addr_array[23], minimum_delegate * 10)
        stake_tx3 = self._stake_tx(self._addr_array[24], minimum_delegate * 10)
        prev_block, tx_results, main_prep_list = self._make_and_req_block([stake_tx1, stake_tx2, stake_tx3])
        self.assertIsNone(main_prep_list)
        self._write_precommit_state(prev_block)
        self._set_revision(REV_DECENTRALIZATION)

        # register preps
        reg_prep_tx_list = []
        for i, address in enumerate(self._main_preps):
            data: dict = {
                ConstantKeys.NAME: "name",
                ConstantKeys.EMAIL: "email",
                ConstantKeys.WEBSITE: "website",
                ConstantKeys.DETAILS: "json",
                ConstantKeys.P2P_END_POINT: "ip",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: IISS_MIN_IREP
            }
            reg_prep_tx_list.append(self._reg_prep_tx(address, data))

        prev_block, tx_results, main_prep_list = self._make_and_req_block(reg_prep_tx_list)
        self.assertIsNone(main_prep_list)
        self._write_precommit_state(prev_block)

        # delegate
        delegate_info = [{"address": str(address), "value": hex(minimum_delegate)}
                         for address in self._addr_array[:10]]
        delegate_tx1 = self._delegate_tx(self._addr_array[22], delegate_info)

        delegate_info = [{"address": str(address), "value": hex(minimum_delegate)}
                         for address in self._addr_array[10:20]]
        delegate_tx2 = self._delegate_tx(self._addr_array[23], delegate_info)

        delegate_info = [{"address": str(address), "value": hex(minimum_delegate)}
                         for address in self._addr_array[20:22]]
        delegate_tx3 = self._delegate_tx(self._addr_array[24], delegate_info)

        prev_block, tx_results, main_prep_list = self._make_and_req_block([delegate_tx1, delegate_tx2, delegate_tx3])
        self.assertIsNotNone(main_prep_list)
        self._write_precommit_state(prev_block)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getMainPRepList",
                "params": {}
            }
        }
        # check if sorted correctly
        initial_main_preps_response = self._query(query_request)
        additional_delegate = _MINIMUM_DELEGATE + 1
        # stake
        stake_tx = self._stake_tx(self._admin, additional_delegate)

        # delegate 10000 to last prep
        last_address = self._main_preps[PREP_MAIN_PREPS - 1]
        delegations = [{
            "address": str(last_address),
            "value": hex(additional_delegate)
        }]
        delegate_tx = self._delegate_tx(self._admin, delegations)
        prev_block, tx_results, main_prep_list = self._make_and_req_block([stake_tx, delegate_tx])
        self._write_precommit_state(prev_block)
        self.assertIsNone(main_prep_list)

        for i in range(_TERM-2):
            prev_block, tx_results, main_prep_list = self._make_and_req_block([])
            self._write_precommit_state(prev_block)
            self.assertIsNone(main_prep_list)

        # check returning main_prep_list after decentralized(Term==10)
        prev_block, tx_results, main_prep_list = self._make_and_req_block([])
        self._write_precommit_state(prev_block)
        self.assertIsNotNone(main_prep_list)

        main_preps_response = self._query(query_request)
        self.assertEqual(initial_main_preps_response['totalDelegated']+additional_delegate,
                         main_preps_response['totalDelegated'])
        self.assertEqual(main_preps_response['preps'][0]['address'], last_address)
