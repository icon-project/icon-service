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
import time
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

        tx = {
            'method': 'icx_sendTransaction',
            'params': params
        }

        block_height: int = get_block_height()
        data: str = f'block_height{block_height}'
        block_hash: bytes = hashlib.sha3_256(data.encode()).digest()
        block_timestamp_us = int(time.time() * 10 ** 6)
        
        try:
            tx_results = engine.invoke(block_height=block_height,
                                       block_hash=block_hash,
                                       block_timestamp=block_timestamp_us,
                                       transactions=[tx])

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
    def __init__(self, port, ip_address=None):
        self.__port = port
        self.__ip_address = ip_address

        self.__server = FlaskServer()
        self.__server.set_resource()

    def run(self):
        logging.error(f"SimpleRestServer run... {self.__port}")

        self.__server.app.run(port=self.__port,
                              host=self.__ip_address,
                              debug=False)


def main():
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = './tbears.json'

    print(f'config_file: {path}')
    conf = load_config(path)

    init_type_converter()
    init_icon_service_engine(conf)

    server = SimpleRestServer(conf['port'])
    server.run()


def load_config(path: str) -> dict:
    default_conf = {
        "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "port": 9000,
        "score_root": "./.score",
        "db_root": "./db",
        "genesis": {
            "address": "hx0000000000000000000000000000000000000000",
            "balance": "0x2961fff8ca4a62327800000"
        },
        "treasury": {
            "address": "hx1000000000000000000000000000000000000000",
            "balance": "0x0"
        }
    }

    try:
        with open(path) as f:
            conf = json.load(f)
    except:
        return default_conf

    for key in default_conf:
        if key not in conf:
            conf[key] = default_conf[key]

    return conf


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


def init_icon_service_engine(conf):
    global _icon_service_engine

    _icon_service_engine = IconServiceEngine()
    _icon_service_engine.open(icon_score_root_path=conf['score_root'],
                              state_db_root_path=conf['db_root'])

    genesis = _type_converter.convert(conf['genesis'], recursive=False)
    treasury = _type_converter.convert(conf['treasury'], recursive=False)

    _icon_service_engine.genesis_invoke([genesis, treasury])


if __name__ == '__main__':
    main()
