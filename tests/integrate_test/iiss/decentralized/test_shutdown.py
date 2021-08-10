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
from typing import List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import DataType
from iconservice.icon_constant import ICX_IN_LOOP, Revision
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestShutdown(TestIISSBase):
    def setUp(self):
        super().setUp()
        self.init_decentralized()
        self.init_inv()

        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=2000 * ICX_IN_LOOP
        )

    def test_shutdown_revision(self):
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        revision = Revision.SHUTDOWN.value
        from_ = self._admin
        to = GOVERNANCE_SCORE_ADDRESS
        params = {"code": hex(revision), "name": f"1.1.{revision}"}

        tx = self.create_score_call_tx(
            from_=self._admin,
            to_=to,
            func_name="setRevision",
            params=params,
        )
        block, tx_results, _, _, _, is_shutdown = self.debug_make_and_req_block([tx])
        assert is_shutdown
