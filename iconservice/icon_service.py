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
import os
import signal

import argparse
import setproctitle
import sys

from earlgrey import MessageQueueService, aio_pika, asyncio

from iconcommons.icon_config import IconConfig
from iconcommons.logger import Logger
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ICON_SERVICE_PROCTITLE_FORMAT, ICON_SCORE_QUEUE_NAME_FORMAT, ConfigKey
from iconservice.icon_inner_service import IconScoreInnerService
from iconservice.icon_service_cli import ICON_SERVICE_CLI, ExitCode

ICON_SERVICE = 'IconService'


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
            Logger.info(f'Start IconService Service serve!', ICON_SERVICE)

        channel = config[ConfigKey.CHANNEL]
        amqp_key = config[ConfigKey.AMQP_KEY]
        amqp_target = config[ConfigKey.AMQP_TARGET]
        score_root_path = config[ConfigKey.SCORE_ROOT_PATH]
        db_root_path = config[ConfigKey.STATE_DB_ROOT_PATH]

        self._set_icon_score_stub_params(channel, amqp_key, amqp_target)

        Logger.info(f'==========IconService Service params==========', ICON_SERVICE)
        Logger.info(f'score_root_path : {score_root_path}', ICON_SERVICE)
        Logger.info(f'icon_score_state_db_root_path  : {db_root_path}', ICON_SERVICE)
        Logger.info(f'amqp_target  : {amqp_target}', ICON_SERVICE)
        Logger.info(f'amqp_key  :  {amqp_key}', ICON_SERVICE)
        Logger.info(f'icon_score_queue_name  : {self._icon_score_queue_name}', ICON_SERVICE)
        Logger.info(f'==========IconService Service params==========', ICON_SERVICE)

        self._inner_service = IconScoreInnerService(amqp_target, self._icon_score_queue_name, conf=config)

        loop = MessageQueueService.loop
        loop.create_task(_serve())
        loop.add_signal_handler(signal.SIGINT, self.close)
        loop.add_signal_handler(signal.SIGTERM, self.close)

        try:
            loop.run_forever()
        finally:
            """
            If the function is called when the operation is not an endless loop 
            in an asynchronous function, the await is terminated immediately.
            """
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def close(self):
        self._inner_service.clean_close()

    def _set_icon_score_stub_params(self, channel: str, amqp_key: str, amqp_target: str):
        self._icon_score_queue_name = \
            ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)
        self._amqp_target = amqp_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-sc", dest=ConfigKey.SCORE_ROOT_PATH, type=str, default=None,
                        help="icon score root path  example : .score")
    parser.add_argument("-st", dest=ConfigKey.STATE_DB_ROOT_PATH, type=str, default=None,
                        help="icon score state db root path  example : .statedb")
    parser.add_argument("-ch", dest=ConfigKey.CHANNEL, type=str, default=None,
                        help="icon score channel")
    parser.add_argument("-ak", dest=ConfigKey.AMQP_KEY, type=str, default=None,
                        help="icon score amqp_key : [amqp_key]")
    parser.add_argument("-at", dest=ConfigKey.AMQP_TARGET, type=str, default=None,
                        help="icon score amqp_target : [127.0.0.1]")
    parser.add_argument("-c", dest=ConfigKey.CONFIG, type=str, default=None,
                        help="icon score config")
    parser.add_argument("-tbears", dest=ConfigKey.TBEARS_MODE, action='store_true',
                        help="tbears mode")
    args = parser.parse_args()

    args_params = dict(vars(args))
    del args_params['config']
    setproctitle.setproctitle(ICON_SERVICE_PROCTITLE_FORMAT.format(**args_params))

    conf_path = args.config
    if conf_path is not None:
        if not IconConfig.valid_conf_path(conf_path):
            print(f'invalid config file : {conf_path}')
            sys.exit(ExitCode.COMMAND_IS_WRONG.value)
    if conf_path is None:
        conf_path = str()

    conf = IconConfig(conf_path, default_icon_config)
    conf.load()
    conf.update_conf(dict(vars(args)))
    Logger.load_config(conf)
    Logger.print_config(conf, ICON_SERVICE_CLI)

    _run_async(_check_rabbitmq(conf[ConfigKey.AMQP_TARGET]))
    icon_service = IconService()
    icon_service.serve(config=conf)
    Logger.info(f'==========IconService Done==========', ICON_SERVICE_CLI)


def run_in_foreground(conf: 'IconConfig'):
    _run_async(_check_rabbitmq(conf[ConfigKey.AMQP_TARGET]))
    icon_service = IconService()
    icon_service.serve(config=conf)


def _run_async(async_func):
    loop = MessageQueueService.loop
    return loop.run_until_complete(async_func)


async def _check_rabbitmq(amqp_target: str):
    connection = None
    try:
        amqp_user_name = os.getenv("AMQP_USERNAME", "guest")
        amqp_password = os.getenv("AMQP_PASSWORD", "guest")
        connection = await aio_pika.connect(host=amqp_target, login=amqp_user_name, password=amqp_password)
        connection.connect()
    except ConnectionRefusedError:
        Logger.error("rabbitmq-service disable", ICON_SERVICE_CLI)
        exit(0)
    finally:
        if connection:
            await connection.close()

if __name__ == '__main__':
    main()
