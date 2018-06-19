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
import aio_pika

import iconservice
from .icon_inner_service import IconScoreInnerStub, IconScoreInnerService
from .icon_config import ICON_SCORE_QUEUE_NAME_FORMAT
from .logger import Logger

ICON_SERVICE_STANDALONE = 'IconServiceStandAlone'


class ExitCode(IntEnum):
    SUCCEEDED = 1
    COMMAND_IS_WRONG = 0


def main():
    parser = argparse.ArgumentParser(prog='icon_service_cli.py', usage=f"""
    ==========================
    iconservice version : {iconservice.__version__}
    ==========================
    iconservice commands:
        serve : icon_service serve
        stop : icon_service stop
    """)

    parser.add_argument('command', type=str,
                        nargs='*',
                        choices=['serve', 'stop'],
                        help='iconservice type [serve|stop]')

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
    parser.add_argument("--rpc_port", type=str, default='9000',
                        help="icon score rpc_port : [9000]")

    args = parser.parse_args()

    if len(args.command) < 1:
        parser.print_help()
        sys.exit(ExitCode.COMMAND_IS_WRONG.value)

    command = args.command[0]

    params = {'--type': args.type,
              '--icon_score_root_path': args.score_root_path,
              '--icon_score_state_db_root_path': args.state_db_root_path,
              '--channel': args.channel, '--amqp_key': args.amqp_key,
              '--amqp_target': args.amqp_target, '--rpc_port': args.rpc_port}

    if command == 'serve' and len(args.command) == 1:
        result = serve(params)
    elif command == 'stop' and len(args.command) == 1:
        result = stop(params)
    else:
        parser.print_help()
        result = ExitCode.COMMAND_IS_WRONG.value
    sys.exit(result)


def serve(params: dict) -> int:
    async def _serve():
        check_serve = await is_serve_icon_service(params)
        if not check_serve:
            await start_process(params)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_serve())
    return ExitCode.SUCCEEDED


def stop(params: dict) -> int:
    async def _stop():
        check_serve = await is_serve_icon_service(params)
        if check_serve:
            kw_params = {'channel': params['--channel'],
                         'amqp_key': params['--amqp_key'],
                         'amqp_target': params['--amqp_target'],
                         'rpc_port': params['--rpc_port']}
            await stop_process(**kw_params)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_stop())
    return ExitCode.SUCCEEDED


async def start_process(params: dict):
    Logger.debug('start_server() start')
    python_module_string = 'iconservice.icon_service'

    custom_argv = []
    for k, v in params.items():
        custom_argv.append(k)
        custom_argv.append(v)

    subprocess.Popen([sys.executable, '-m', python_module_string, *custom_argv], close_fds=True)
    Logger.debug('start_process() end')


async def stop_process(channel: str, amqp_key: str, amqp_target: str, rpc_port: str):
    icon_score_queue_name = _make_icon_score_queue_name(channel, amqp_key, rpc_port)
    stub = await _create_icon_score_stub(amqp_target, icon_score_queue_name)
    await stub.async_task().close()
    Logger.info(f'stop_icon_service!', ICON_SERVICE_STANDALONE)


async def is_serve_icon_service(params: dict) -> bool:
    kw_params = {'channel': params['--channel'],
                 'amqp_key': params['--amqp_key'],
                 'amqp_target': params['--amqp_target'],
                 'rpc_port': params['--rpc_port']}
    return await _check_serve(**kw_params)


async def _check_serve(channel: str, amqp_key: str, amqp_target: str, rpc_port: str) -> bool:
    icon_score_queue_name = _make_icon_score_queue_name(channel, amqp_key, rpc_port)
    Logger.info(f'check_serve_icon_service!', ICON_SERVICE_STANDALONE)

    try:
        kw_params = {'exclusive': True}
        connection = await aio_pika.connect_robust(f"amqp://{amqp_target}")
        channel = await connection.channel()

        queue = await channel.declare_queue(icon_score_queue_name, auto_delete=True)
        await queue.consume(_consume, **kw_params)
    except:
        return True
    return False


async def _consume(message):
    pass


def _make_icon_score_queue_name(channel: str, amqp_key: str, rpc_port: str) -> str:
    return ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key, rpc_port=rpc_port)


async def _create_icon_score_stub(amqp_target: str, icon_score_queue_name: str) -> 'IconScoreInnerStub':
    stub = IconScoreInnerStub(amqp_target, icon_score_queue_name)
    await stub.connect()
    return stub
