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
from unittest.mock import Mock

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import Revision, ICX_IN_LOOP
from iconservice.iiss import IISSMethod
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISS(TestIISSBase):
    def test_iiss_query_via_icx_sendtransaction(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 100 icx
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # IScore query mocking
        block_height = 10 ** 2
        icx = 10 ** 3
        iscore = icx * 10 ** 3
        RewardCalcProxy.query_iscore = Mock(return_value=(iscore, block_height))

        iiss_query_method = [IISSMethod.QUERY_ISCORE, IISSMethod.GET_DELEGATION, IISSMethod.GET_STAKE]

        # TEST : query via icx_sendTransaction (revision < ALLOW_INVOKE_SYSTEM_SCORE_READONLY)
        for method in iiss_query_method:
            self.check_query_via_icx_sendtransaction(method, False)

        # TEST : query via icx_sendTransaction (revision >= ALLOW_INVOKE_SYSTEM_SCORE_READONLY)
        self.set_revision(Revision.SYSTEM_SCORE_ENABLED.value)
        for method in iiss_query_method:
            self.check_query_via_icx_sendtransaction(method, True)

    def check_query_via_icx_sendtransaction(self, method: str, expected_status: bool):
        tx = self.create_score_call_tx(from_=self._admin,
                                       to_=SYSTEM_SCORE_ADDRESS,
                                       func_name=method,
                                       params={"address": str(self._accounts[0].address)})
        return self.process_confirm_block_tx([tx], expected_status=expected_status)

