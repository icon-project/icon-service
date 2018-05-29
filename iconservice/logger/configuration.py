# Copyright [theloop]
#
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

import logging
import coloredlogs
from enum import IntEnum
from logging.handlers import TimedRotatingFileHandler


class LogHandlerType(IntEnum):
    console = 1
    file_only_one = 2
    debug = 3
    file = 4
    production = 5


class LogConfiguration:
    def __init__(self):
        self.log_format = None
        self.custom = ""
        self.log_level = logging.DEBUG
        self.log_color = True
        self.__handler_type = LogHandlerType.console
        self.__log_file_path = None
        self.__log_format = None

    def log_file_path(self, log_file_path: str):
        self.__log_file_path = log_file_path

    def update_logger(self, logger: logging.Logger=None):
        self.__log_format = self.log_format.replace("TAG", self.custom)

        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        if logger is None:
            handlers = self.__make_handler()
            logging.basicConfig(handlers= handlers,
                                format=self.__log_format, datefmt="%m-%d %H:%M:%S", level=self.log_level)
        else:
            logger.setLevel(self.log_level)

        if self.log_color:
            self.__update_log_color_set(logger)

    def set_handler(self, handler_type: LogHandlerType=LogHandlerType.debug):
        self.__handler_type = handler_type

    def __make_handler(self) -> []:
        handlers = []
        if LogHandlerType.console & self.__handler_type:
            handlers.append(logging.StreamHandler())
        if LogHandlerType.file_only_one & self.__handler_type == LogHandlerType.file_only_one:
            handlers.append(logging.FileHandler(self.__log_file_path, 'w', 'utf-8'))
        if LogHandlerType.file & self.__handler_type == LogHandlerType.file:
            handlers.append(TimedRotatingFileHandler(self.__log_file_path, when='D'))
        return handlers

    def __update_log_color_set(self, logger):
        coloredlogs.DEFAULT_FIELD_STYLES = {
            'hostname': {'color': 'magenta'},
            'programname': {'color': 'cyan'},
            'name': {'color': 'blue'},
            'levelname': {'color': 'black', 'bold': True},
            'asctime': {'color': 'magenta'}}

        coloredlogs.DEFAULT_LEVEL_STYLES = {
            'info': {},
            'notice': {'color': 'magenta'},
            'verbose': {'color': 'blue'},
            'success': {'color': 'green', 'bold': True},
            'spam': {'color': 'cyan'},
            'critical': {'color': 'red', 'bold': True},
            'error': {'color': 'red'},
            'debug': {'color': 'green'},
            'warning': {'color': 'yellow'}}

        coloredlogs.install(logger=logger,
                            fmt=self.__log_format,
                            datefmt="%m%d %H:%M:%S",
                            level=self.log_level,
                            milliseconds=True)
