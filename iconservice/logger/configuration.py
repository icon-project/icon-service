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
import os

from enum import IntEnum
from logging.handlers import TimedRotatingFileHandler


class LogHandlerType(IntEnum):
    NONE = 0
    CONSOLE = 1
    FILE = 2
    DAILY = 4


class LogConfiguration:
    def __init__(self):
        self.log_format = None
        self.custom = ""
        self.log_level = logging.DEBUG
        self.log_color = False
        self.__handler_type = LogHandlerType.CONSOLE
        self.__log_file_path = None
        self.__log_format = None

    def log_file_path(self, log_file_path: str):
        self._ensure_dir(log_file_path)
        self.__log_file_path = log_file_path

    @staticmethod
    def _ensure_dir(file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    log_file_path = property(None, log_file_path)

    def update_logger(self, logger: logging.Logger=None):
        if logger is None:
            logger = logging.root

        self.__log_format = self.log_format.replace("TAG", self.custom)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        if logger is logging.root:
            handlers = self.__make_handler()
            logging.basicConfig(handlers= handlers,
                                format=self.__log_format,
                                datefmt="%m-%d %H:%M:%S",
                                level=self.log_level)

            if self.log_color:
                self.__update_log_color_set(logger)
        else:
            logger.setLevel(self.log_level)

    def set_handler(self, handler_type: LogHandlerType):
        self.__handler_type = handler_type

    def __make_handler(self) -> []:
        handlers = []

        if self.__handler_type & LogHandlerType.CONSOLE:
            handlers.append(logging.StreamHandler())

        if self.__handler_type & LogHandlerType.FILE:
            handlers.append(
                logging.FileHandler(self.__log_file_path, 'w', 'utf-8'))

        if self.__handler_type & LogHandlerType.DAILY:
            handlers.append(
                TimedRotatingFileHandler(self.__log_file_path, when='D'))

        return handlers

    def __update_log_color_set(self, logger):
        coloredlogs.DEFAULT_FIELD_STYLES = {
            'hostname': {'color': 'magenta'},
            'programname': {'color': 'cyan'},
            'name': {'color': 'blue'},
            'levelname': {'color': 'black', 'bold': True},
            'asctime': {'color': 'magenta'}}

        coloredlogs.DEFAULT_LEVEL_STYLES = {
            'info': {'color': 'green'},
            'notice': {'color': 'magenta'},
            'verbose': {'color': 'blue'},
            'success': {'color': 'green', 'bold': True},
            'spam': {'color': 'cyan'},
            'critical': {'color': 'red', 'bold': True},
            'error': {'color': 'red'},
            'debug': {'color': 'white'},
            'warning': {'color': 'yellow'}}

        coloredlogs.install(logger=logger,
                            fmt=self.__log_format,
                            datefmt="%m-%d %H:%M:%S",
                            level=self.log_level,
                            milliseconds=True)
