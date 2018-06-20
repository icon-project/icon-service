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
import sys
import subprocess
from enum import IntEnum
import asyncio

import iconservice
from .icon_inner_service import IconScoreInnerStub
from .icon_config import ICON_SCORE_QUEUE_NAME_FORMAT
from .logger import Logger

ICON_SERVICE_STANDALONE = 'IconServiceStandAlone'


class ExitCode(IntEnum):
    SUCCEEDED = 1
    COMMAND_IS_WRONG = 0


def main():
    parser = argparse.ArgumentParser(prog='icon_service_cli.py', usage=f"""
    ==========================
    iconservice version : {iconservice.__version__}pwd
    ==========================
    iconservice commands:
        start : icon_service start
        stop : icon_service stop
    """)

    parser.add_argument('command', type=str,
                        nargs='*',
                        choices=['start', 'stop'],
                        help='iconservice type [start|stop]')

    parser.add_argument("--type", type=str, default='user',
                        choices=['tbears', 'user'],
                        help="icon service type [tbears|user]")
    parser.add_argument("--score_root_path", type=str, default='.score',
                        help="icon score root path  example : .score")
    parser.add_argument("--state_db_root_path", type=str, default='.db',
                        help="icon score state db root path  example : .db")
    parser.add_argument("--channel", type=str, default='loopchain_default',
                        help="icon score channel")
    parser.add_argument("--amqp_key", type=str, default='amqp_key',
                        help="icon score amqp_key : [amqp_key]")
    parser.add_argument("--amqp_target", type=str, default='127.0.0.1',
                        help="icon score amqp_target : [127.0.0.1]")

    args = parser.parse_args()

    if len(args.command) < 1:
        parser.print_help()
        sys.exit(ExitCode.COMMAND_IS_WRONG.value)

    command = args.command[0]

    params = {'--type': args.type,
              '--icon_score_root_path': args.score_root_path,
              '--icon_score_state_db_root_path': args.state_db_root_path,
              '--channel': args.channel, '--amqp_key': args.amqp_key,
              '--amqp_target': args.amqp_target}

    if command == 'start' and len(args.command) == 1:
        result = start(params)
    elif command == 'stop' and len(args.command) == 1:
        result = stop(params)
    else:
        parser.print_help()
        result = ExitCode.COMMAND_IS_WRONG.value
    sys.exit(result)


def start(params: dict) -> int:
    if not is_serve_icon_service(params):
        start_process(params)
    return ExitCode.SUCCEEDED


def stop(params: dict) -> int:
    async def _stop():
        kw_params = {'channel': params['--channel'],
                     'amqp_key': params['--amqp_key'],
                     'amqp_target': params['--amqp_target']}
        await stop_process(**kw_params)

    if is_serve_icon_service(params):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_stop())

    return ExitCode.SUCCEEDED


def start_process(params: dict):
    Logger.debug('start_server() start')
    python_module_string = 'iconservice.icon_service'

    custom_argv = []
    for k, v in params.items():
        custom_argv.append(k)
        custom_argv.append(v)

    subprocess.Popen([sys.executable, '-m', python_module_string, *custom_argv], close_fds=True)
    Logger.debug('start_process() end')


async def stop_process(channel: str, amqp_key: str, amqp_target: str):
    icon_score_queue_name = _make_icon_score_queue_name(channel, amqp_key)
    stub = await _create_icon_score_stub(amqp_target, icon_score_queue_name)
    await stub.async_task().close()
    Logger.info(f'stop_icon_service!', ICON_SERVICE_STANDALONE)


def is_serve_icon_service(params: dict) -> bool:
    kw_params = {'channel': params['--channel'],
                 'amqp_key': params['--amqp_key'],
                 'amqp_target': params['--amqp_target']}
    return _check_serve(**kw_params)


def _check_serve(channel: str, amqp_key: str, amqp_target: str) -> bool:
    Logger.info(f'check_serve_icon_service!', ICON_SERVICE_STANDALONE)
    return find_procs_by_params('icon_service', channel, amqp_key, amqp_target)


def find_procs_by_params(name, *args) -> bool:
    # Return a list of processes matching 'name'.

    key_table = ['--channel', '--amqp_key', '--amqp_target']

    command = f"ps -ef | grep {name} | grep -v grep"
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
    if result.returncode == 1:
        return False

    result = result.stdout.decode()
    lines = result.splitlines()
    for line_str in lines:
        params = line_str.split('Python -m iconservice.icon_service ')
        if len(params) != 2:
            continue

        options = params[1]
        option_params = options.split(' ')
        option_table = dict(zip(option_params[::2], option_params[1::2]))
        for index in range(len(args)):
            if option_table[key_table[index]] != args[index]:
                return False
    return True


def _make_icon_score_queue_name(channel: str, amqp_key: str) -> str:
    return ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)


async def _create_icon_score_stub(amqp_target: str, icon_score_queue_name: str) -> 'IconScoreInnerStub':
    stub = IconScoreInnerStub(amqp_target, icon_score_queue_name)
    await stub.connect()
    return stub
