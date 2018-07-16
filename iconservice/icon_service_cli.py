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
import json
import os
import sys
import subprocess
from enum import IntEnum
import asyncio

from .icon_constant import ICON_SCORE_QUEUE_NAME_FORMAT, ICON_SERVICE_PROCTITLE_FORMAT
from .logger import Logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .icon_inner_service import IconScoreInnerStub

ICON_SERVICE_STANDALONE = 'IconServiceStandAlone'
DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))
CONFIG_JSON_PATH = os.path.join(DIRECTORY_PATH, "icon_service.json")


class ExitCode(IntEnum):
    SUCCEEDED = 0
    COMMAND_IS_WRONG = 1


def main():
    parser = argparse.ArgumentParser(prog='icon_service_cli.py', usage=f"""
    ==========================
    iconservice
    ==========================
    iconservice commands:
        start : icon_service start
        stop : icon_service stop
    """)

    parser.add_argument('command', type=str,
                        nargs='*',
                        choices=['start', 'stop'],
                        help='iconservice type [start|stop]')
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

    if len(args.command) < 1:
        parser.print_help()
        sys.exit(ExitCode.COMMAND_IS_WRONG.value)

    Logger(args.config)

    cli_config = get_config(vars(args))  # get config dict

    command = args.command[0]
    if command == 'start' and len(args.command) == 1:
        result = start(cli_config)
    elif command == 'stop' and len(args.command) == 1:
        result = stop(cli_config)
    else:
        parser.print_help()
        result = ExitCode.COMMAND_IS_WRONG.value
    sys.exit(result)


def start(params: dict) -> int:
    if not is_serve_icon_service(params):
        start_process(params)
    Logger.info(f'start_command done!', ICON_SERVICE_STANDALONE)
    return ExitCode.SUCCEEDED


def stop(params: dict) -> int:
    async def _stop():
        await stop_process(params)

    if is_serve_icon_service(params):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_stop())

    Logger.info(f'stop_command done!', ICON_SERVICE_STANDALONE)
    return ExitCode.SUCCEEDED


def start_process(params: dict):
    Logger.debug('start_server() start')
    python_module_string = 'iconservice.icon_service'

    converted_params = {'-t': params['type'],
                        '-sc': params['icon_score_root_path'],
                        '-st': params['icon_score_state_db_root_path'],
                        '-ch': params['channel'], '-ak': params['amqp_key'],
                        '-at': params['amqp_target'], '-c': params['config']}

    custom_argv = []
    for k, v in converted_params.items():
        custom_argv.append(k)
        custom_argv.append(v)

    subprocess.Popen([sys.executable, '-m', python_module_string, *custom_argv], close_fds=True)
    Logger.debug('start_process() end')


async def stop_process(params: dict):
    icon_score_queue_name = _make_icon_score_queue_name(params['channel'], params['amqp_key'])
    stub = await _create_icon_score_stub(params['amqp_target'], icon_score_queue_name)
    await stub.async_task().close()
    Logger.info(f'stop_process_icon_service!', ICON_SERVICE_STANDALONE)


def is_serve_icon_service(params: dict) -> bool:
    return _check_serve(params)


def _check_serve(params: dict) -> bool:
    Logger.info(f'check_serve_icon_service!', ICON_SERVICE_STANDALONE)
    proc_title = ICON_SERVICE_PROCTITLE_FORMAT.format(**params)
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


async def _create_icon_score_stub(
        amqp_target: str, icon_score_queue_name: str) -> 'IconScoreInnerStub':
    from .icon_inner_service import IconScoreInnerStub

    stub = IconScoreInnerStub(amqp_target, icon_score_queue_name)
    await stub.connect()
    return stub


def get_config(args_config: dict):
    try:
        with open(args_config['config'], mode='rb') as config_file:
            config = json.load(config_file)
            config = config['input_cli']
        config_dict = {k: v for k, v in args_config.items() if k != "command"}
        params_dict = {}

        for k in config_dict:
            if k in config:
                config_dict[k] = config[k]
            params_dict[f'{k}'] = config_dict[k]

    except:
        Logger.error('check your config file!')
        sys.exit(ExitCode.COMMAND_IS_WRONG)
    else:
        return params_dict
