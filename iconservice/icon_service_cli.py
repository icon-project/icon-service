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
import os
import sys
import subprocess
from enum import IntEnum
import asyncio
import signal

from .icon_constant import ICON_SCORE_QUEUE_NAME_FORMAT, ICON_SERVICE_PROCTITLE_FORMAT, ConfigKey
from .icon_config import default_icon_config
from iconcommons.icon_config import IconConfig
from iconcommons.logger import Logger

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .icon_inner_service import IconScoreInnerStub

ICON_SERVICE_STANDALONE = 'IconServiceStandAlone'
DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))
CONFIG_JSON_PATH = os.path.join(DIRECTORY_PATH, "icon_service.json")
cache_conf = None


class ExitCode(IntEnum):
    SUCCEEDED = 0
    COMMAND_IS_WRONG = 1


def signal_handler(signum, frame):
    global cache_conf
    if cache_conf:
        Logger.info(f'signal_handler conf: {cache_conf}')
        _stop(cache_conf)
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(prog='icon_service_cli.py', usage=f"""
    ==========================
    iconservice
    ==========================
    iconservice commands:
        start : iconservice start
        stop : iconservice stop
        
        -c : json configure file path
        -sc : icon score root path ex).score
        -st : icon score state db root path ex).state
        -at : amqp target info [IP]:[PORT]
        -ak : key sharing peer group using queue name. use it if one more peers connect one MQ
        -ch : loopchain channel ex) loopchain_default
        -fg : foreground process
    """)

    parser.add_argument('command', type=str,
                        nargs='*',
                        choices=['start', 'stop'],
                        help='iconservice type [start|stop]')
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
    parser.add_argument("-fg", dest='foreground', action='store_true',
                        help="icon score service run foreground")

    args = parser.parse_args()

    if len(args.command) < 1:
        parser.print_help()
        sys.exit(ExitCode.COMMAND_IS_WRONG.value)

    conf = IconConfig(args.config, default_icon_config)
    conf.load(dict(vars(args)))
    Logger.load_config(conf)

    global cache_conf
    cache_conf = conf

    command = args.command[0]
    if command == 'start' and len(args.command) == 1:
        result = _start(conf)
    elif command == 'stop' and len(args.command) == 1:
        result = _stop(conf)
    else:
        parser.print_help()
        result = ExitCode.COMMAND_IS_WRONG.value
    sys.exit(result)


def _start(conf: 'IconConfig') -> int:
    if not _is_running_icon_service(conf):
        _start_process(conf)
    Logger.info(f'start_command done!', ICON_SERVICE_STANDALONE)
    return ExitCode.SUCCEEDED


def _stop(conf: 'IconConfig') -> int:
    async def __stop():
        await stop_process(conf)

    if _is_running_icon_service(conf):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(__stop())

    Logger.info(f'stop_command done!', ICON_SERVICE_STANDALONE)
    return ExitCode.SUCCEEDED


def _start_process(conf: 'IconConfig'):
    Logger.debug('start_server() start')
    python_module_string = 'iconservice.icon_service'

    converted_params = {'-sc': conf[ConfigKey.SCORE_ROOT_PATH],
                        '-st': conf[ConfigKey.STATE_DB_ROOT_PATH],
                        '-ch': conf[ConfigKey.CHANNEL], '-ak': conf[ConfigKey.AMQP_KEY],
                        '-at': conf[ConfigKey.AMQP_TARGET], '-c': conf.get(ConfigKey.CONFIG)}

    custom_argv = []
    for k, v in converted_params.items():
        if v is None:
            continue
        custom_argv.append(k)
        custom_argv.append(str(v))

    is_foreground = conf.get('foreground', False)
    if is_foreground:
        from iconservice.icon_service import run_in_foreground
        del conf['foreground']
        run_in_foreground(conf)
    else:
        subprocess.Popen([sys.executable, '-m', python_module_string, *custom_argv], close_fds=True)
    Logger.debug('start_process() end')


async def stop_process(conf: 'IconConfig'):
    icon_score_queue_name = _make_icon_score_queue_name(conf[ConfigKey.CHANNEL], conf[ConfigKey.AMQP_KEY])
    stub = await _create_icon_score_stub(conf[ConfigKey.AMQP_TARGET], icon_score_queue_name)
    await stub.async_task().close()
    Logger.info(f'stop_process_icon_service!', ICON_SERVICE_STANDALONE)


def _is_running_icon_service(conf: 'IconConfig') -> bool:
    return _check_service_running(conf)


def _check_service_running(conf: 'IconConfig') -> bool:
    Logger.info(f'check_serve_icon_service!', ICON_SERVICE_STANDALONE)
    proc_title = ICON_SERVICE_PROCTITLE_FORMAT.format(**
                                                      {ConfigKey.SCORE_ROOT_PATH: conf[ConfigKey.SCORE_ROOT_PATH],
                                                       ConfigKey.STATE_DB_ROOT_PATH: conf[ConfigKey.STATE_DB_ROOT_PATH],
                                                       ConfigKey.CHANNEL: conf[ConfigKey.CHANNEL],
                                                       ConfigKey.AMQP_KEY: conf[ConfigKey.AMQP_KEY],
                                                       ConfigKey.AMQP_TARGET: conf[ConfigKey.AMQP_TARGET]})
    return find_procs_by_params(proc_title)


def find_procs_by_params(name) -> bool:
    # Return a list of processes matching 'name'.
    command = f"ps -ef | grep {name} | grep -v grep"
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
    if result.returncode == 1:
        return False
    return True


def _make_icon_score_queue_name(channel: str, amqp_key: str) -> str:
    return ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)


async def _create_icon_score_stub(amqp_target: str, icon_score_queue_name: str) -> 'IconScoreInnerStub':
    from .icon_inner_service import IconScoreInnerStub

    stub = IconScoreInnerStub(amqp_target, icon_score_queue_name)
    await stub.connect()
    return stub
