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
import subprocess
import sys
from enum import IntEnum
from typing import TYPE_CHECKING

from iconcommons.icon_config import IconConfig
from iconcommons.logger import Logger

from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ICON_SCORE_QUEUE_NAME_FORMAT, ICON_SERVICE_PROCTITLE_FORMAT, ConfigKey
from .__version__ import __version__

if TYPE_CHECKING:
    from .icon_inner_service import IconScoreInnerStub

_TAG = "CLI"


class ExitCode(IntEnum):
    SUCCEEDED = 0
    INVALID_COMMAND = 1


def main():
    parser = argparse.ArgumentParser(prog='icon_service_cli.py', usage=f"""
    ==========================
    iconservice {__version__}
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
        -tbears : tbears mode
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
    parser.add_argument("-tbears", dest=ConfigKey.TBEARS_MODE, action='store_true',
                        help="tbears mode")
    parser.add_argument("-steptrace", dest=ConfigKey.STEP_TRACE_FLAG, action="store_true", help="enable step tracing")

    args = parser.parse_args()

    if len(args.command) < 1:
        parser.print_help()
        sys.exit(ExitCode.INVALID_COMMAND.value)

    conf_path = args.config

    if conf_path is not None:
        if not IconConfig.valid_conf_path(conf_path):
            print(f'invalid config file : {conf_path}')
            sys.exit(ExitCode.INVALID_COMMAND.value)
    if conf_path is None:
        conf_path = str()

    conf = IconConfig(conf_path, copy.deepcopy(default_icon_config))
    conf.load()
    conf.update_conf(dict(vars(args)))
    Logger.load_config(conf)

    command = args.command[0]
    if command == 'start' and len(args.command) == 1:
        result = _start(conf)
    elif command == 'stop' and len(args.command) == 1:
        result = _stop(conf)
    else:
        parser.print_help()
        result = ExitCode.INVALID_COMMAND.value
    sys.exit(result)


def _start(conf: 'IconConfig') -> int:
    if not _check_if_process_running(conf):
        _start_process(conf)
    Logger.info(f'start_command done!', _TAG)
    return ExitCode.SUCCEEDED


def _stop(conf: 'IconConfig') -> int:
    async def __stop():
        await stop_process(conf)

    if _check_if_process_running(conf):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(__stop())

    Logger.info(f'stop_command done!', _TAG)
    return ExitCode.SUCCEEDED


def _start_process(conf: 'IconConfig'):
    Logger.info('start_server() start')
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
    if conf[ConfigKey.TBEARS_MODE]:
        custom_argv.append('-tbears')
    if conf[ConfigKey.STEP_TRACE_FLAG]:
        custom_argv.append('-steptrace')

    is_foreground = conf.get('foreground', False)
    if is_foreground:
        from iconservice.icon_service import run_in_foreground
        del conf['foreground']
        run_in_foreground(conf)
    else:
        subprocess.Popen([sys.executable, '-m', python_module_string, *custom_argv], close_fds=True)
    Logger.info('start_process() end')


async def stop_process(conf: 'IconConfig'):
    icon_score_queue_name = _make_icon_score_queue_name(conf[ConfigKey.CHANNEL], conf[ConfigKey.AMQP_KEY])
    stub = await _create_icon_score_stub(conf[ConfigKey.AMQP_TARGET], icon_score_queue_name)
    await stub.async_task().close()
    Logger.info(f'stop_process_icon_service!', _TAG)


def _check_if_process_running(conf: 'IconConfig') -> bool:
    proc_title = ICON_SERVICE_PROCTITLE_FORMAT.format(**
                                                      {ConfigKey.SCORE_ROOT_PATH: conf[ConfigKey.SCORE_ROOT_PATH],
                                                       ConfigKey.STATE_DB_ROOT_PATH: conf[ConfigKey.STATE_DB_ROOT_PATH],
                                                       ConfigKey.CHANNEL: conf[ConfigKey.CHANNEL],
                                                       ConfigKey.AMQP_KEY: conf[ConfigKey.AMQP_KEY],
                                                       ConfigKey.AMQP_TARGET: conf[ConfigKey.AMQP_TARGET]})
    cmd_lines = _get_process_command_list(b'icon_service.')
    if cmd_lines:
        for cmdline in cmd_lines:
            if cmdline == proc_title:
                return True
    return False


def _get_process_command_list(prefix: bytes) -> list:
    if os.path.exists('/proc'):
        cmd_lines = []
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
        for pid in pids:
            try:
                cmdpath = os.path.join('/proc', pid, 'cmdline')
                cmdline = open(cmdpath, 'rb').read().rstrip(b'\x00')
                if cmdline.startswith(prefix):
                    cmd_lines.append(cmdline.decode())
            except IOError:
                continue
    else:
        result = subprocess.run(['ps', '-eo', 'command'], stdout=subprocess.PIPE)
        cmd_lines = [cmdline.decode().rstrip()
                     for cmdline in result.stdout.split(b'\n')
                     if cmdline.startswith(prefix)]
    return cmd_lines


def _make_icon_score_queue_name(channel: str, amqp_key: str) -> str:
    return ICON_SCORE_QUEUE_NAME_FORMAT.format(channel_name=channel, amqp_key=amqp_key)


async def _create_icon_score_stub(amqp_target: str, icon_score_queue_name: str) -> 'IconScoreInnerStub':
    from .icon_inner_service import IconScoreInnerStub

    stub = IconScoreInnerStub(amqp_target, icon_score_queue_name)
    await stub.connect()
    return stub
