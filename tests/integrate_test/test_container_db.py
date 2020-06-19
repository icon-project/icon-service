# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

import os
from typing import TYPE_CHECKING, List

from iconservice import Address
from iconservice.icon_constant import PREP_MAIN_PREPS, IISS_DB, Revision
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.utils import int_to_bytes
from tests.integrate_test.test_integrate_base import EOAAccount, TestIntegrateBase

if TYPE_CHECKING:
    pass


# In this test, do not check about the IPC
class TestContainerDB(TestIntegrateBase):
    def tearDown(self):
        super().tearDown()

    def _close_and_reopen_iconservice(self):
        self.icon_service_engine.close()
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self._config)

    def test_reopen(self):
        #
        self.update_governance()
        self.set_revision(revision=Revision.FOUR.value)
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_array_db2",
            from_=self._accounts[0],
            expected_status=True
        )
        score_address: 'Address' = tx_results[0].score_address

        for i in range(10):
            self.score_call(
                from_=self._accounts[0],
                to_=score_address,
                func_name="set_values",
                params={"i": hex(i)}
            )

        ret = self.query_score(
            from_=self._accounts[0],
            to_=score_address,
            func_name="get_values"
        )

        assert [i for i in range(10)] == ret

        self._close_and_reopen_iconservice()

        for i in range(10, 20):
            self.score_call(
                from_=self._accounts[0],
                to_=score_address,
                func_name="set_values",
                params={"i": hex(i)}
            )

        ret = self.query_score(
            from_=self._accounts[0],
            to_=score_address,
            func_name="get_values"
        )

        assert [i for i in range(20)] == ret
