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
from iconservice.icon_constant import ICX_IN_LOOP, Revision
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIntegrateCall(TestIISSBase):
    def test_invalid_eoa_call(self):
        self.init_decentralized()
        self.init_inv()

        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=balance
        )

        self.score_call(
            from_=self._accounts[0],
            to_=self._accounts[1].address,
            func_name="test",
        )

        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        self.score_call(
            from_=self._accounts[0],
            to_=self._accounts[1].address,
            func_name="test",
            pre_validation_enabled=False,
            expected_status=False
        )
