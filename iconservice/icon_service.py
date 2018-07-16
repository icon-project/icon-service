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

import argparse
import setproctitle

from earlgrey import MessageQueueService
from iconservice.icon_inner_service import IconScoreInnerService
from iconservice.icon_config import Configure
from iconservice.icon_constant import ICON_SERVICE_PROCTITLE_FORMAT, ICON_SCORE_QUEUE_NAME_FORMAT,\
    DEFAULT_ICON_SERVICE_FOR_TBEARS_ARGUMENT
from iconservice.logger import Logger
from iconservice.icon_service_cli import ICON_SERVICE_STANDALONE, CONFIG_JSON_PATH


class IconService(object):
    """IconScore service for stand alone start.
    It provides gRPC interface for peer_service to communicate with icon service.
    Its role is the bridge between loopchain and IconServiceEngine.
    """

    def __init__(self):
        self._icon_score_queue_name = None
        self._amqp_target = None
        self._inner_service = None

    def serve(self, icon_score_root_path: str, icon_score_state_db_root_path: str, channel: str, amqp_key: str,
              amqp_target: str, config: 'Configure'):
        async def _serve():
            await self._inner_service.connect(exclusive=True)
            Logger.info(f'Start IconService Service serve!', ICON_SERVICE_STANDALONE)

        self._set_icon_score_stub_params(channel, amqp_key, amqp_target)

        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_root_path : {icon_score_root_path}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_state_db_root_path  : {icon_score_state_db_root_path}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'amqp_target  : {self._amqp_target}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_queue_name  : {self._icon_score_queue_name}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)

        self._inner_service = IconScoreInnerService(amqp_target, self._icon_score_queue_name,
                                                    icon_score_root_path=icon_score_root_path,
                                                    icon_score_state_db_root_path=icon_score_state_db_root_path,
                                                    conf=config)

        loop = MessageQueueService.loop
        loop.create_task(_serve())
        loop.run_forever()

    def _set_icon_score_stub_params(self, channel: str, amqp_key: str, amqp_target: str):
        self._icon_score_queue_name = \
            ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)
        self._amqp_target = amqp_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", dest='type', type=str, default='user',
                        choices=['tbears', 'user'],
                        help="icon service type [tbears|user]")
    parser.add_argument("-sc", dest='icon_score_root_path', type=str, default='.score',
                        help="icon score root path  example : .score")
    parser.add_argument("-st", dest='icon_score_state_db_root_path', type=str, default='.db',
                        help="icon score state db root path  example : .db")
    parser.add_argument("-ch", dest='channel', type=str, default='loopchain_default',
                        help="icon score channel")
    parser.add_argument("-ak", dest='amqp_key', type=str, default='amqp_key',
                        help="icon score amqp_key : [amqp_key]")
    parser.add_argument("-at", dest='amqp_target', type=str, default='127.0.0.1',
                        help="icon score amqp_target : [127.0.0.1]")
    parser.add_argument("-c", dest='config', type=str, default=CONFIG_JSON_PATH,
                        help="icon score config")
    args = parser.parse_args()

    args_params = dict(vars(args))
    setproctitle.setproctitle(ICON_SERVICE_PROCTITLE_FORMAT.format(**args_params))

    del args_params['type']
    del args_params['config']

    Logger(args.config)
    conf = Configure(args.config)

    args_params['config'] = conf

    icon_service = IconService()
    if args.type == "tbears":
        icon_service.serve(**DEFAULT_ICON_SERVICE_FOR_TBEARS_ARGUMENT)
    else:
        icon_service.serve(**args_params)
    Logger.debug(f'==========IconService Done==========', ICON_SERVICE_STANDALONE)


if __name__ == '__main__':
    main()
