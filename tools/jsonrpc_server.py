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

# import _ssl
import json
import logging
import sys
import hashlib
# import ssl
# import threading
sys.path.append('..')
sys.path.append('.')

from flask import Flask, request, Response
from flask_restful import reqparse, Api
from jsonrpcserver import methods

from iconservice.icon_service_engine import IconServiceEngine
from iconservice.base.address import Address
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.utils.type_converter import TypeConverter


_type_converter = None
_icon_service_engine = None
_block_height = 0


def get_icon_service_engine():
    return _icon_service_engine


def get_block_height():
    global _block_height
    _block_height += 1

    return _block_height


class MockDispatcher:

    @staticmethod
    def dispatch():
        req = json.loads(request.get_data().decode())
        # req["params"] = req.get("params", None)

        response = methods.dispatch(req)
        return Response(str(response),
                        response.http_status,
                        mimetype='application/json')

    @staticmethod
    @methods.add
    def icx_sendTransaction(**kwargs):
        """icx_sendTransaction jsonrpc handler

        We assume that only one tx in a block

        :param params: jsonrpc params field
        """
        engine = get_icon_service_engine()

        params = _type_converter.convert(kwargs, recursive=False)

        tx ={}
        tx['params'] = params
        tx['method'] = 'icx_sendTransaction'

        transactions = [tx]

        block_height: int = get_block_height()
        data: str = f'block_height{block_height}'
        block_hash: bytes = hashlib.sha3_256(data.encode()).digest()
        block_timestamp_us = 0
        
        try:
            tx_results = engine.invoke(block_height=block_height,
                                       block_hash=block_hash,
                                       block_timestamp=block_timestamp_us,
                                       transactions=transactions)

            tx_result = tx_results[0]
            if tx_result.status == TransactionResult.SUCCESS:
                engine.commit()
            else:
                engine.rollback()
        except:
            engine.rollback()
            raise

        return tx_result.to_dict()

    """
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
    """

    @staticmethod
    @methods.add
    def icx_getBalance(**params):
        engine = get_icon_service_engine()

        # params['address'] = Address.from_string(params['address'])
        params = _type_converter.convert(params, recursive=False)
        value = engine.query(method='icx_getBalance', params=params)

        return hex(value)

    @staticmethod
    @methods.add
    def icx_getTotalSupply(**params):
        engine = get_icon_service_engine()

        value: int = engine.query(method='icx_getTotalSupply', params=params)

        return hex(value)


class FlaskServer():
    def __init__(self):
        self.__app = Flask(__name__)
        self.__api = Api(self.__app)
        self.__parser = reqparse.RequestParser()

        # SSL 적용 여부에 따라 context 생성 여부를 결정한다.
        # if conf.REST_SSL_TYPE == conf.SSLAuthType.none:
        #     self.__ssl_context = None
        # elif conf.REST_SSL_TYPE == conf.SSLAuthType.server_only:
        #     self.__ssl_context = (conf.DEFAULT_SSL_CERT_PATH, conf.DEFAULT_SSL_KEY_PATH)
        # elif conf.REST_SSL_TYPE == conf.SSLAuthType.mutual:
        #     self.__ssl_context = ssl.SSLContext(_ssl.PROTOCOL_SSLv23)
        #
        #     self.__ssl_context.verify_mode = ssl.CERT_REQUIRED
        #     self.__ssl_context.check_hostname = False
        #
        #     self.__ssl_context.load_verify_locations(cafile=conf.DEFAULT_SSL_TRUST_CERT_PATH)
        #     self.__ssl_context.load_cert_chain(conf.DEFAULT_SSL_CERT_PATH, conf.DEFAULT_SSL_KEY_PATH)
        # else:
        #     utils.exit_and_msg(
        #         f"REST_SSL_TYPE must be one of [0,1,2]. But now conf.REST_SSL_TYPE is {conf.REST_SSL_TYPE}")

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


class SimpleRestServer():
    def __init__(self, peer_port, peer_ip_address=None):
        # if peer_ip_address is None:
        #     peer_ip_address = conf.IP_LOCAL
        # CommonThread.__init__(self)
        self.__peer_port = peer_port
        self.__peer_ip_address = peer_ip_address

        self.__server = FlaskServer()
        self.__server.set_resource()

    def run(self):
        # ScoreInvoker().init_stub(self.__peer_ip_address, self.__peer_port)
        # ScoreInvoker().score_load()
        api_port = self.__peer_port + 1900 #conf.PORT_DIFF_REST_SERVICE_CONTAINER
        logging.error("SimpleRestServer run... %s", str(api_port))

        # event.set()
        self.__server.app.run(port=api_port,
                              host=self.__peer_ip_address,
                              debug=False)


def main():
    init_type_converter()
    init_icon_service_engine()

    server = SimpleRestServer(7100)
    server.run()


def init_type_converter():
    global _type_converter

    type_table = {
        'from': 'address',
        'to': 'address',
        'address': 'address',
        'fee': 'int',
        'value': 'int',
        'balance': 'int'
    }
    _type_converter = TypeConverter(type_table)


def init_icon_service_engine():
    global _icon_service_engine

    _icon_service_engine = IconServiceEngine()
    _icon_service_engine.open('./score_root', './db_root')

    with open('init_genesis.json') as f:
        genesis_block = json.load(f)

    accounts = genesis_block['transaction_data']['accounts']
    accounts = _type_converter.convert(accounts, recursive=True)

    _icon_service_engine.genesis_invoke(accounts)


if __name__ == '__main__':
    main()
