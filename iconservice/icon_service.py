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

from message_queue import MessageQueueService
from iconservice.icon_inner_service import IconScoreInnerService, IconScoreInnerStub
from iconservice.icon_config import *
from iconservice.logger import Logger

ICON_SERVICE_STANDALONE = 'IconServiceStandAlone'


class IconService(object):
    """IconScore service for stand alone start.
    It provides gRPC interface for peer_service to communicate with icon service.
    Its role is the bridge between loopchain and IconServiceEngine.
    """

    def __init__(self, icon_score_root_path: str, icon_score_state_db_root_path: str,
                 channel: str, amqp_key: str, amqp_target: str, rpc_port: str, only_inner_service: bool = False):
        """constructor
        """

        self.__icon_score_stub = None
        icon_score_queue_name = ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel,
                                                                    amqp_key=amqp_key,
                                                                    rpc_port=rpc_port)

        self.__icon_score_queue_name = icon_score_queue_name
        self.__only_inner_service = only_inner_service

        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_root_path : {icon_score_root_path}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_state_db_root_path  : {icon_score_state_db_root_path}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'amqp_target  : {amqp_target}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_queue_name  : {icon_score_queue_name}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'only_service : {only_inner_service}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)

        self.__amqp_target = amqp_target
        self.__inner_service = IconScoreInnerService(amqp_target, self.__icon_score_queue_name,
                                                     icon_score_root_path=icon_score_root_path,
                                                     icon_score_state_db_root_path=icon_score_state_db_root_path)

    def stop(self):
        if not self.__only_inner_service:
            self.__icon_score_stub().task().close()

        self.__inner_service.loop.stop()
        self.__inner_service.loop.close()

    async def __create_icon_score_stub(self):
        stub = IconScoreInnerStub(self.__amqp_target, self.__icon_score_queue_name)
        await stub.connect()
        self.__icon_score_stub = stub

    def serve(self):
        async def __serve():
            await self.__inner_service.connect(exclusive=True)

            if not self.__only_inner_service:
                await self.__create_icon_score_stub()
                await self.__icon_score_stub.task().open()

            Logger.info(f'Start IconService Service serve!', ICON_SERVICE_STANDALONE)

        loop = MessageQueueService.loop
        loop.create_task(__serve())
        loop.run_forever()


def main(argv):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--type", type=str, default='tbears',
                        choices=['tbears', 'user'],
                        help="icon service type [tbears|user]")
    parser.add_argument("--score_root_path", type=str, default='.score',
                        help="icon score root path  example : .score")
    parser.add_argument("--state_db_root_path", type=str, default='.db',
                        help="icon score state db root path  example : .db")
    parser.add_argument("--channel", type=str,
                        help="icon score channel")
    parser.add_argument("--amqp_key", type=str, default='amqp_key',
                        help="icon score amqp_key : [amqp_key]")
    parser.add_argument("--amqp_target", type=str, default='127.0.0.1',
                        help="icon score amqp_target : [127.0.0.1]")
    parser.add_argument("--rpc_port", type=str, default='9000',
                        help="icon score rpc_port : [9000]")
    parser.add_argument("--only_inner_service", type=bool, default=False,
                        help="icon score only_inner_service")

    args = parser.parse_args(argv)

    path = './icon_service.json'
    Logger(path)

    if args.type == "tbears":
        icon_service = IconService(**DEFAULT_ICON_SERVICE_FOR_TBEARS_ARGUMENT)
    else:
        params = {'icon_score_root_path': args.score_root_path,
                  'icon_score_state_db_root_path': args.state_db_root_path,
                  'channel': args.channel, 'amqp_key': args.amqp_key,
                  'amqp_target': args.amqp_target, 'rpc_port': args.rpc_port,
                  'only_inner_service': args.only_inner_service}
        icon_service = IconService(**params)

    icon_service.serve()


if __name__ == '__main__':
    import sys

    main(sys.argv[1:])
