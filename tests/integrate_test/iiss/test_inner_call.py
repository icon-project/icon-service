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

from iconservice.icon_constant import ConfigKey
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSBaseTransactionValidation(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_inner_call(self):
        inner_call_request = {"method": "ise_getPRepList"}
        inner_call_response: dict = self.inner_call(inner_call_request)
        self.assertNotIn("preps", inner_call_response)

        self.init_decentralized()
        inner_call_response: dict = self.inner_call(inner_call_request)
        self.assertEqual(len(inner_call_response['result']['preps']), 22)
