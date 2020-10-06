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

import argparse
import asyncio
import copy
import os
import signal
import sys

import aio_pika
import pkg_resources
import setproctitle
from earlgrey import MessageQueueService

from iconcommons.icon_config import IconConfig
from iconcommons.logger import Logger
from iconservice.base.exception import FatalException
from iconservice.icon_config import default_icon_config, check_config, args_to_dict
from iconservice.icon_constant import ICON_SERVICE_PROCTITLE_FORMAT, ICON_SCORE_QUEUE_NAME_FORMAT, ConfigKey
from iconservice.icon_inner_service import IconScoreInnerService
from iconservice.icon_service_cli import ExitCode

_TAG = 'CLI'


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
            Logger.info(f'Start IconService Service serve!', _TAG)

        channel = config[ConfigKey.CHANNEL]
        amqp_key = config[ConfigKey.AMQP_KEY]
        amqp_target = config[ConfigKey.AMQP_TARGET]
        score_root_path = config[ConfigKey.SCORE_ROOT_PATH]
        db_root_path = config[ConfigKey.STATE_DB_ROOT_PATH]
        version: str = get_version()

        self._set_icon_score_stub_params(channel, amqp_key, amqp_target)

        Logger.info(f'==========IconService Service params==========', _TAG)

        Logger.info(f'version : {version}', _TAG)
        Logger.info(f'score_root_path : {score_root_path}', _TAG)
        Logger.info(f'icon_score_state_db_root_path  : {db_root_path}', _TAG)
        Logger.info(f'amqp_target  : {amqp_target}', _TAG)
        Logger.info(f'amqp_key  :  {amqp_key}', _TAG)
        Logger.info(f'icon_score_queue_name  : {self._icon_score_queue_name}', _TAG)
        Logger.info(f'==========IconService Service params==========', _TAG)

        # Before creating IconScoreInnerService instance,
        # loop SHOULD be set as a current event loop for the current thread.
        # Otherwise connection between iconservice and rc will be failed.
        loop = MessageQueueService.loop
        asyncio.set_event_loop(loop)

        try:
            self._inner_service = IconScoreInnerService(amqp_target, self._icon_score_queue_name, conf=config)
        except FatalException as e:
            Logger.exception(f"{e}", _TAG)
            Logger.error(f"{e}", _TAG)
            self._inner_service.clean_close()

        loop.create_task(_serve())
        loop.add_signal_handler(signal.SIGINT, self.signal_handler, signal.SIGINT)
        loop.add_signal_handler(signal.SIGTERM, self.signal_handler, signal.SIGTERM)

        try:
            loop.run_forever()
        except FatalException as e:
            Logger.exception(f"{e}", _TAG)
            Logger.error(f"{e}", _TAG)
            self._inner_service.clean_close()
        finally:
            """
            If the function is called when the operation is not an endless loop 
            in an asynchronous function, the await is terminated immediately.
            """
            Logger.info(f"loop has been stopped and will be closed.")

            loop.run_until_complete(loop.shutdown_asyncgens())

            self.cancel_tasks(loop)

            # close icon service components
            self._inner_service.clean_close()

            loop.close()

    @staticmethod
    def cancel_tasks(loop):
        pending = asyncio.Task.all_tasks(loop)
        Logger.info(f"cancel pending {len(pending)} tasks in event loop.")
        for task in pending:
            if task.done():
                continue
            task.cancel()
            try:
                loop.run_until_complete(task)
            except asyncio.CancelledError as e:
                Logger.info(f"cancel pending task: {task}, error: {e}")

    @staticmethod
    def signal_handler(signum: int):
        Logger.debug(f"Get signal {signum}")
        asyncio.get_event_loop().stop()

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
    parser.add_argument("-steptrace", dest=ConfigKey.STEP_TRACE_FLAG, action="store_true", help="enable step tracing")

    args = parser.parse_args()

    args_params = dict(vars(args))
    del args_params['config']
    setproctitle.setproctitle(ICON_SERVICE_PROCTITLE_FORMAT.format(**args_params))

    conf_path = args.config
    if conf_path is not None:
        if not IconConfig.valid_conf_path(conf_path):
            print(f'invalid config file : {conf_path}')
            sys.exit(ExitCode.INVALID_COMMAND.value)
    if conf_path is None:
        conf_path = str()

    conf = IconConfig(conf_path, copy.deepcopy(default_icon_config))
    conf.load()
    conf.update_conf(args_to_dict(args))
    Logger.load_config(conf)
    if not check_config(conf, default_icon_config):
        Logger.error(tag=_TAG, msg=f"Invalid Config")
        sys.exit(ExitCode.INVALID_CONFIG.value)

    Logger.print_config(conf, _TAG)

    _run_async(_check_rabbitmq(conf[ConfigKey.AMQP_TARGET]))
    icon_service = IconService()
    icon_service.serve(config=conf)
    Logger.info(f'==========IconService Done==========', _TAG)


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
    except ConnectionRefusedError:
        Logger.error("rabbitmq-service disable", _TAG)
        exit(0)
    finally:
        if connection:
            await connection.close()


DIR_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(DIR_PATH, '..'))


def get_version() -> str:
    """Get version of iconservice.
    The location of the file that holds the version information is different when packaging and when executing.
    :return: version of tbears.
    """
    try:
        version = pkg_resources.get_distribution('iconservice').version
    except pkg_resources.DistributionNotFound:
        version_path = os.path.join(PROJECT_ROOT_PATH, 'VERSION')
        with open(version_path, mode='r') as version_file:
            version = version_file.read()
    except:
        version = 'unknown'
    return version


if __name__ == '__main__':
    main()
