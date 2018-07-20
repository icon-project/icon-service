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
from iconservice.icon_constant import ICON_SERVICE_PROCTITLE_FORMAT, ICON_SCORE_QUEUE_NAME_FORMAT, ConfigKey

from iconservice.icon_config import default_icon_config
from iconservice.icon_service_cli import ICON_SERVICE_STANDALONE, CONFIG_JSON_PATH
from iconcommons.logger import Logger
from iconcommons.icon_config import IconConfig


class IconService(object):
    """IconScore service for stand alone start.
    It provides gRPC interface for peer_service to communicate with icon service.
    Its role is the bridge between loopchain and IconServiceEngine.
    """

    def __init__(self):
        self._icon_score_queue_name = None
        self._amqp_target = None
        self._inner_service = None

    def serve(self, config: 'IconConfig'):
        async def _serve():
            await self._inner_service.connect(exclusive=True)
            Logger.info(f'Start IconService Service serve!', ICON_SERVICE_STANDALONE)

        channel = config[ConfigKey.CHANNEL]
        amqp_key = config[ConfigKey.AMQP_KEY]
        amqp_target = config[ConfigKey.AMQP_TARGET]
        score_root_path = config[ConfigKey.SCORE_ROOT_PATH]
        db_root_patn = config[ConfigKey.SCORE_STATE_DB_ROOT_PATH]

        self._set_icon_score_stub_params(channel, amqp_key, amqp_target)

        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)
        Logger.debug(f'score_root_path : {score_root_path}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_state_db_root_path  : {db_root_patn}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'amqp_target  : {amqp_target}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'amqp_key  :  {amqp_key}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'icon_score_queue_name  : {self._icon_score_queue_name}', ICON_SERVICE_STANDALONE)
        Logger.debug(f'==========IconService Service params==========', ICON_SERVICE_STANDALONE)

        self._inner_service = IconScoreInnerService(amqp_target, self._icon_score_queue_name, conf=config)

        loop = MessageQueueService.loop
        loop.create_task(_serve())
        loop.run_forever()

    def _set_icon_score_stub_params(self, channel: str, amqp_key: str, amqp_target: str):
        self._icon_score_queue_name = \
            ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)
        self._amqp_target = amqp_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-sc", dest=ConfigKey.SCORE_ROOT_PATH, type=str, default=None,
                        help="icon score root path  example : .score")
    parser.add_argument("-st", dest=ConfigKey.SCORE_STATE_DB_ROOT_PATH, type=str, default=None,
                        help="icon score state db root path  example : .statedb")
    parser.add_argument("-ch", dest=ConfigKey.CHANNEL, type=str, default=None,
                        help="icon score channel")
    parser.add_argument("-ak", dest=ConfigKey.AMQP_KEY, type=str, default=None,
                        help="icon score amqp_key : [amqp_key]")
    parser.add_argument("-at", dest=ConfigKey.AMQP_TARGET, type=str, default=None,
                        help="icon score amqp_target : [127.0.0.1]")
    parser.add_argument("-c", dest=ConfigKey.CONFIG, type=str, default=CONFIG_JSON_PATH,
                        help="icon score config")
    args = parser.parse_args()

    args_params = dict(vars(args))
    del args_params['config']
    setproctitle.setproctitle(ICON_SERVICE_PROCTITLE_FORMAT.format(**args_params))

    conf = IconConfig(args.config, default_icon_config)
    conf.load(args_params)
    Logger.load_config(conf)

    icon_service = IconService()
    icon_service.serve(config=conf)
    Logger.debug(f'==========IconService Done==========', ICON_SERVICE_STANDALONE)


def run_in_foreground(conf: 'IconConfig'):
    icon_service = IconService()
    icon_service.serve(config=conf)


if __name__ == '__main__':
    main()
