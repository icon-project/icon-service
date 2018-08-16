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

import unittest

from iconcommons.icon_config import IconConfig
from iconservice import ExceptionCode
from iconservice.base.address import AddressPrefix
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_address, create_block_hash, raise_exception_start_tag, raise_exception_end_tag
from integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateSimpleInvoke(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self._addr1 = create_address(AddressPrefix.EOA)

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)
        self._inner_task._open()

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_sys_call(self):
        request = {'method': 'sys_getLastBlack', 'params': {}}
        ret = self._run_async(self._sys_call(request))
        print(ret)

    def test_invoke_success(self):
        value1 = 1 * self._icx_factor

        validate_tx_response, tx = self._run_async(self._make_icx_send_tx(self._genesis_addr, self._addr1, value1))
        self.assertEqual(validate_tx_response, hex(0))
        precommit_req, tx_results = self._run_async(self._make_and_req_block([tx]))
        tx_result = self._get_tx_result(tx_results, tx)
        self.assertEqual(tx_result['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req))
        self.assertEqual(response, hex(0))

        query_request = {
            "address": str(self._addr1)
        }
        response = self._run_async(self._query(query_request, 'icx_getBalance'))
        self.assertEqual(response, hex(value1))

        value2 = 2 * self._icx_factor

        validate_tx_response, tx = self._run_async(self._make_icx_send_tx(self._genesis_addr, self._addr1, value2))
        self.assertEqual(validate_tx_response, hex(0))
        precommit_req, tx_results = self._run_async(self._make_and_req_block([tx]))
        tx_result = self._get_tx_result(tx_results, tx)
        self.assertEqual(tx_result['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request, 'icx_getBalance'))
        self.assertEqual(response, hex(value1 + value2))

    def test_make_invalid_block_height(self):
        value1 = 1 * self._icx_factor

        # have to NextBlockHeight[2] != LastBlockHeight[0] + 1 (32000)

        raise_exception_start_tag("test_make_invalid_block_height")
        validate_tx_response, tx = self._run_async(self._make_icx_send_tx(self._genesis_addr, self._addr1, value1))
        self.assertEqual(validate_tx_response, hex(0))
        precommit_req, error_response = self._run_async(self._make_and_req_block([tx], block_height=0))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)

        error_response = self._run_async(self._write_precommit_state(precommit_req))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)

        validate_tx_response, tx = self._run_async(self._make_icx_send_tx(self._genesis_addr, self._addr1, value1))
        self.assertEqual(validate_tx_response, hex(0))
        precommit_req, error_response = self._run_async(self._make_and_req_block([tx], block_height=2))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)

        error_response = self._run_async(self._write_precommit_state(precommit_req))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)
        raise_exception_end_tag("test_make_invalid_block_height")

        query_request = {
            "address": str(self._addr1)
        }

        response = self._run_async(self._query(query_request, 'icx_getBalance'))
        self.assertEqual(response, hex(0))

    def test_make_invalid_block_hash(self):
        value1 = 1 * self._icx_factor

        raise_exception_start_tag("test_make_invalid_block_hash")
        validate_tx_response, tx = self._run_async(self._make_icx_send_tx(self._genesis_addr, self._addr1, value1))
        self.assertEqual(validate_tx_response, hex(0))
        precommit_req, tx_results = self._run_async(
            self._make_and_req_block([tx], block_height=1))
        tx_result = self._get_tx_result(tx_results, tx)
        self.assertEqual(tx_result['status'], hex(True))

        # modulate blockHash
        precommit_req['blockHash'] = bytes.hex(create_block_hash())

        error_response = self._run_async(self._write_precommit_state(precommit_req))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)
        raise_exception_end_tag("test_make_invalid_block_hash")

        query_request = {
            "address": str(self._addr1)
        }

        response = self._run_async(self._query(query_request, 'icx_getBalance'))
        self.assertEqual(response, hex(0))


if __name__ == '__main__':
    unittest.main()
