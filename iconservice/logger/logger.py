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
import json
from .configuration import LogConfiguration, LogHandlerType
from enum import IntEnum

DEFAULT_LOG_FORMAT = "%(asctime)s %(process)d %(thread)d [TAG] %(levelname)s %(message)s"
DEFAULT_LOG_FILE_PATH = "./logger.log"


class LogLevel(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Logger:
    def __init__(self, import_file_path: str=None):
        if import_file_path is None:
            self.__log_preset = self.make_default_preset()
        else:
            self.__log_preset = self.import_file(import_file_path)

    def import_file(self, path: str):
        try:
            with open(path) as f:
                conf = json.load(f)
                logger_config = conf['Logger']
        except:
            return self.make_default_preset()

        return conf
        preset = LogConfiguration()
        return preset

    def make_default_preset(self):
        preset = LogConfiguration()
        preset.log_format = DEFAULT_LOG_FORMAT
        preset.log_level = LogLevel.DEBUG
        preset.log_color = True
        preset.log_file_path = DEFAULT_LOG_FILE_PATH
        preset.set_handler(LogHandlerType.production)
        self.update_other_logger_level('pika')
        self.update_other_logger_level('aio_pika')
        self.update_other_logger_level('sanic.access')
        return preset

    def update_other_logger_level(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        self.__log_preset.update_logger(logger)

    def set_tag(self, tag: str):
        self.__log_preset.custom = tag
        self.__log_preset.update_logger()

    def set_log_level(self, log_level: 'LogLevel'):
        self.__log_preset.log_level = log_level
        self.__log_preset.update_logger()

    def set_handler_type(self, handler_type: 'LogHandlerType'):
        self.__log_preset.set_handler(handler_type)
        self.__log_preset.update_logger()

    @staticmethod
    def info(msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)

    @staticmethod
    def debug(msg, *args, **kwargs):
        logging.debug(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        logging.warning(msg, *args, **kwargs)

    @staticmethod
    def exception(msg, *args, exc_info=True, **kwargs):
        logging.exception(msg, *args, exc_info=exc_info, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logging.error(msg, *args, **kwargs)

