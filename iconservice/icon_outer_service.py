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
"""grpc service for icon service"""

import logging
import json
import pickle

from loopchain.baseservice import ScoreResponse
from loopchain.blockchain import Transaction, Block
from loopchain.protos import loopchain_pb2, loopchain_pb2_grpc, message_code
from iconservice.icon_service_engine import IconServiceEngine

# loopchain_pb2 를 아래와 같이 import 하지 않으면 broadcast 시도시 pickle 오류가 발생함
# import loopchain_pb2


class IconOuterService(loopchain_pb2_grpc.ContainerServicer):
    """Implement grpc server interface for icon service.
    """

    def __init__(self,
                 channel: str,
                 iconscore_root_path: str) -> None:
        """Constructor

        :param channel: loopchain channel name
        :param iconscore_root_path: root path where iconscores are deployed
        """
        self.__iconscore_root_path = iconscore_root_path
        self.__icon_service_engine = IconServiceEngine()

        self.__handler_map = {
            message_code.Request.status: self.__handler_status,
            message_code.Request.is_alive: self.__handler_is_alive,
            message_code.Request.stop: self.__handler_stop,
            message_code.Request.genesis_invoke: self.__handler_genesis_invoke,
            message_code.Request.score_load: self.__handler_score_load,
            message_code.Request.score_invoke: self.__handler_score_invoke,
            message_code.Request.score_query: self.__handler_score_query,
            message_code.Request.score_set: self.__handler_score_set,
            message_code.Request.score_connect: self.__handler_connect,
            message_code.Request.score_write_precommit_state: self.__handler_write_precommit_state,
            message_code.Request.score_remove_precommit_state: self.__handler_remove_precommit_state,
            message_code.Request.score_change_block_hash: self.__handler_change_block_hash
        }

    def __handler_connect(self, request, context) -> loopchain_pb2.Message:
        """Make a stub to communicate with peer_service

        :param request: message=target of peer_service
        :param context:
        :return:
        """
        return loopchain_pb2.Message(code=message_code.Response.fail)

    def __handler_status(self, request, context) -> loopchain_pb2.Message:
        """Returns icon service status

        :param request:
        :param context:
        :return:
        """
        logging.debug("score_service handler_status")

        status = {}
        status_json = json.dumps(status)

        return loopchain_pb2.Message(code=message_code.Response.success,
                                     meta=status_json)

    def __handler_is_alive(self, request, context):
        """Check whether icon service is alive.

        :param request:
        :param context:
        :return:
        """
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_stop(self, request, context):
        """Stop icon service

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug("IconOuterService handler stop...")
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_score_load(self, request, context):
        """Load already deployed icon scores.

        TODO: loading icon scores

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug(f"ScoreService Score Load Request : {request}")
        return loopchain_pb2.Message(code=message_code.Response.success, meta="")

    def __handler_genesis_invoke(self, request, context):
        """handles a genesis transaction.

        TODO
        This method should be called only once before creating a genesis block.

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug(f"ScoreService Score Genesis Invoke Request: {request}")
        return loopchain_pb2.Message(code=message_code.Response.success, meta="")

    def __handler_score_invoke(self, request, context) -> loopchain_pb2.Message:
        """handles transactions which cause icon score state change.

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        block: Block = pickle.loads(request.object)

        logging.debug(f"ScoreService Score Invoke Request: {request}")
        logging.debug(f"ScoreService score_invoke height: {block.height}, hash: {block.block_hash}")

        results = {}

        for transaction in block.confirmed_transaction_list:
            if not isinstance(transaction, Transaction):
                continue

            tx_hash = transaction.get_tx_hash()
            if tx_hash:
                result_code: message_code = self.__invoke(transaction, block)
                results[tx_hash] = {
                    'code': result_code
                }

        commit_state = {"TEST", "VALUE1234"}  # TODO: dummy state
        meta = json.dumps(results)

        return loopchain_pb2.Message(
            code=message_code.Response.success,
            meta=meta,
            object=pickle.dumps(commit_state))

    def __invoke(self, transaction, block):
        """
        """
        # self.__icon_service_engine.invoke()
        return message_code.Response.success  # TODO: dummy

    def __handler_score_query(self, request, context):
        """ do query using request.meta and return json.dumps response

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug(f"ScoreService Score Query Request: {request}")
        ret = self.__query(request.meta)
        return loopchain_pb2.Message(code=message_code.Response.success, meta=ret)

    def __query(self, message: str) -> str:
        """Execute query message with IconServiceEngine

        :param message: message in json format
        :return: response in json format
        """

        params = json.loads(message)
        method = params['method']
        del params['method']

        # ret = self.__icon_service_engine.query(method, params)
        ret = json.dumps({'code': ScoreResponse.EXCEPTION, 'message': 'There is no score'})  # TODO: dummy
        return ret

    def __handler_score_set(self, request, context):
        """IconService doesn't need this handler, but how about loopchain engine?

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_write_precommit_state(self, request, context):
        """Write precommit state to persistent storage like levelDB.

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug(f"ScoreService Write Precommit State: {request}")
        commit_state = json.loads(request.meta)
        # TODO:
        # IcxEngine.commit_block_state(commit_state['block_height'], commit_state['block_hash'])
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_remove_precommit_state(self, request, context):
        """Remove precommit states

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        # TODO: There is no place invoking this function!
        # TODO: The invocation has been commented out in CandidateBlocks::get_confirmed_block()
        return loopchain_pb2.Message(code=message_code.Response.success)

    def __handler_change_block_hash(self, request, context):
        """loopchain informs icon service that
        block hash is changed because some failed txs are found.

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """
        logging.debug(f"ScoreService Change Block Hash: {request}")
        block_info = json.loads(request.meta)
        # TODO:
        # IcxEngine.change_block_hash(block_height=block_info['block_height'],
        #                             old_block_hash=block_info['old_block_hash'],
        #                             new_block_hash=block_info['new_block_hash'])
        return loopchain_pb2.Message(code=message_code.Response.success)

    def Request(self, request, context):
        """grpc interface

        :param request: (object) grpc parameter
        :param context: (object) grpc parameter
        :return: (object) grpc Message
        """

        if request.code in self.__handler_map:
            return self.__handler_map[request.code](request, context)

        return loopchain_pb2.Message(
            code=message_code.Response.not_treat_message_code)
