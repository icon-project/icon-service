# Copyright 2018 theloop Inc.
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

import grpc
import json
import leveldb
import logging

from cli_tools.icx_test.mock_peer import set_mock
from loopchain import configure as conf
from loopchain.blockchain import Block, BlockStatus
from loopchain.blockchain import BlockChain
from loopchain.components import SingletonMetaClass
from loopchain.peer import IcxAuthorization
from loopchain.protos import loopchain_pb2, loopchain_pb2_grpc, message_code
from testcase.unittest import test_util


class ScoreInvoker(metaclass=SingletonMetaClass):
    """ Simple SCORE client for local testing
    """
    DB_NAME = 'db_test'

    def __init__(self):
        logging.info(f"*** {__name__} init")
        self.__stub = None
        self.__channel = conf.LOOPCHAIN_DEFAULT_CHANNEL
        self.peer_auth = IcxAuthorization(self.__channel)

        test_db = test_util.make_level_db(self.DB_NAME)
        self.chain = BlockChain(test_db)

    def init_stub(self, host, port):
        logging.info("*** init_stub()")
        channel = grpc.insecure_channel(f'{str(host)}:{int(port)}')
        self.__stub = loopchain_pb2_grpc.ContainerStub(channel)
        set_mock(self, self.__channel, self.__stub)

    def cleanup(self):
        logging.info("*** cleanup()")
        leveldb.DestroyDB(self.DB_NAME)

    def score_load(self):
        logging.info("*** score_load()")
        params = dict()
        params["foo"] = "bar"
        meta = json.dumps(params)

        response = self.__stub.Request(loopchain_pb2.Message(
            code=message_code.Request.score_load,
            meta=meta))
        logging.info(f"Response: {response}")

    def add_genesis_block(self):
        logging.info("*** add_genesis_block()")
        block = test_util.add_genesis_block()
        self.chain.add_block(block)

    def send_transaction(self, tx):
        logging.info("*** send_transaction()")
        # make a block
        block = Block(self.__channel)
        block.put_transaction(tx)
        if self.chain.last_block is None:
            self.add_genesis_block()
        logging.info(f" --- chain last_block hash: {self.chain.last_block.block_hash}")
        block.generate_block(self.chain.last_block)
        block.block_status = BlockStatus.confirmed
        self.chain.add_block(block)

        # TODO: how to handle failed message?
        return loopchain_pb2.Message(code=message_code.Response.success, message=tx.tx_hash)

    def get_invoke_result(self, tx_hash):
        logging.info("*** get_invoke_result()")
        invoke_result = self.chain.find_invoke_result_by_tx_hash(tx_hash)
        invoke_result_str = json.dumps(invoke_result)
        logging.info(f" --- invoke_result : {invoke_result_str}")
        return loopchain_pb2.GetInvokeResultReply(
            response_code=message_code.Response.success,
            result=invoke_result_str)

    def get_balance(self, meta):
        logging.info("*** get_balance()")
        params = json.loads(meta)
        if 'address' not in params.keys():
            return loopchain_pb2.Message(code=message_code.Response.fail_illegal_params)

        response = self.__stub.Request(loopchain_pb2.Message(
            code=message_code.Request.score_query,
            meta=meta))
        logging.info(f" --- get_balance: response({response})")
        return loopchain_pb2.Message(code=message_code.Response.success, meta=response.meta)

    def get_total_supply(self, meta):
        logging.info("*** get_total_supply()")
        response = self.__stub.Request(loopchain_pb2.Message(
            code=message_code.Request.score_query,
            meta=meta))
        logging.info(f" --- get_total_supply: response({response})")
        return loopchain_pb2.Message(code=message_code.Response.success, meta=response.meta)
