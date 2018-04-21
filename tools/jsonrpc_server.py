# Copyright 2017-2018 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import _ssl
import json
import logging
import ssl
import threading

from flask import Flask, request, Response
from flask_restful import reqparse, Api
from jsonrpcserver import methods

from icon.tools.score_invoker import ScoreInvoker
from loopchain import utils, configure as conf, util
from loopchain.baseservice import CommonThread
from loopchain.protos import message_code
from loopchain.rest_server import IcnTxPrevalidator


class MockDispatcher:
    tx_validator = IcnTxPrevalidator()

    @staticmethod
    def dispatch():
        req = json.loads(request.get_data().decode())
        req["params"] = req.get("params", {})
        req["params"]["method"] = request.get_json()["method"]

        response = methods.dispatch(req)
        return Response(str(response), response.http_status, mimetype='application/json')

    @staticmethod
    @methods.add
    def icx_sendTransaction(**kwargs):
        util.logger.spam(f"icx_sendTransaction{kwargs}")
        tx = MockDispatcher.tx_validator.validate_dumped_tx(json.dumps(kwargs), conf.LOOPCHAIN_DEFAULT_CHANNEL)
        if tx is None:
            return {"response_code": message_code.Response.fail_create_tx,
                    "message": f"tx validate fail. tx data :: {kwargs}"}

        # util.logger.spam("********************************************")
        # util.logger.spam(f"{tx.json_dumps()}")
        # util.logger.spam("********************************************")

        # deliver the tx object to IconScoreService directly here!
        res = ScoreInvoker().send_transaction(tx)

        response_data = {'response_code': res.code}
        if res.code != message_code.Response.success:
            response_data['message'] = res.message
        else:
            response_data['tx_hash'] = res.message

        util.logger.spam(f"response_data: ({response_data})")
        return response_data

    @staticmethod
    @methods.add
    def icx_getTransactionResult(**kwargs):
        util.logger.spam(f"icx_getTransactionResult{kwargs}")
        verify_result = {}

        tx_hash = kwargs["tx_hash"]
        if util.is_hex(tx_hash):
            response = ScoreInvoker().get_invoke_result(tx_hash)
            util.logger.spam(f"icx_getTransactionResult::response - {response}")
            verify_result['response_code'] = str(response.response_code)
            if len(response.result) is not 0:
                try:
                    result = json.loads(response.result)
                    verify_result['response'] = result
                except json.JSONDecodeError as e:
                    logging.warning("your data is not json, your data(" + str(response.data) + ")")
                    verify_result['response_code'] = str(message_code.Response.fail.value)
            else:
                verify_result['response_code'] = str(message_code.Response.fail.value)
        else:
            verify_result['response_code'] = str(message_code.Response.fail_validate_params.value)
            verify_result['message'] = "Invalid transaction hash."

        return verify_result

    @staticmethod
    @methods.add
    def icx_getBalance(**kwargs):
        util.logger.spam(f"icx_getBalance{kwargs}")
        response = ScoreInvoker().get_balance(json.dumps(kwargs))
        try:
            response_data = json.loads(response.meta)
        except json.JSONDecodeError as e:
            response_data = json.loads("{}")
            response_data['response'] = response.meta
        response_data['response_code'] = response.code
        return response_data

    @staticmethod
    @methods.add
    def icx_getTotalSupply(**kwargs):
        util.logger.spam(f"icx_getTotalSupply{kwargs}")
        response = ScoreInvoker().get_total_supply(json.dumps(kwargs))
        try:
            response_data = json.loads(response.meta)
        except json.JSONDecodeError as e:
            response_data = json.loads("{}")
            response_data['response'] = response.meta
        response_data['response_code'] = response.code
        return response_data


class FlaskServer():
    def __init__(self):
        self.__app = Flask(__name__)
        self.__api = Api(self.__app)
        self.__parser = reqparse.RequestParser()

        # SSL 적용 여부에 따라 context 생성 여부를 결정한다.
        if conf.REST_SSL_TYPE == conf.SSLAuthType.none:
            self.__ssl_context = None
        elif conf.REST_SSL_TYPE == conf.SSLAuthType.server_only:
            self.__ssl_context = (conf.DEFAULT_SSL_CERT_PATH, conf.DEFAULT_SSL_KEY_PATH)
        elif conf.REST_SSL_TYPE == conf.SSLAuthType.mutual:
            self.__ssl_context = ssl.SSLContext(_ssl.PROTOCOL_SSLv23)

            self.__ssl_context.verify_mode = ssl.CERT_REQUIRED
            self.__ssl_context.check_hostname = False

            self.__ssl_context.load_verify_locations(cafile=conf.DEFAULT_SSL_TRUST_CERT_PATH)
            self.__ssl_context.load_cert_chain(conf.DEFAULT_SSL_CERT_PATH, conf.DEFAULT_SSL_KEY_PATH)
        else:
            utils.exit_and_msg(
                f"REST_SSL_TYPE must be one of [0,1,2]. But now conf.REST_SSL_TYPE is {conf.REST_SSL_TYPE}")

    @property
    def app(self):
        return self.__app

    @property
    def api(self):
        return self.__api

    @property
    def ssl_context(self):
        return self.__ssl_context

    def set_resource(self):
        self.__app.add_url_rule('/api/v2', view_func=MockDispatcher.dispatch, methods=['POST'])


class SimpleRestServer(CommonThread):
    def __init__(self, peer_port, peer_ip_address=None):
        if peer_ip_address is None:
            peer_ip_address = conf.IP_LOCAL
        CommonThread.__init__(self)
        self.__peer_port = peer_port
        self.__peer_ip_address = peer_ip_address

        self.__server = FlaskServer()
        self.__server.set_resource()

    def run(self, event: threading.Event):
        ScoreInvoker().init_stub(self.__peer_ip_address, self.__peer_port)
        ScoreInvoker().score_load()
        api_port = self.__peer_port + conf.PORT_DIFF_REST_SERVICE_CONTAINER
        logging.debug("SimpleRestServer run... %s", str(api_port))

        event.set()
        self.__server.app.run(port=api_port, host=self.__peer_ip_address,
                              debug=False, ssl_context=self.__server.ssl_context)


if __name__ == '__main__':
    server = SimpleRestServer(7100)
    server.start()
