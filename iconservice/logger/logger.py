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
from .configuration import LogConfiguration, LogHandlerType
from enum import IntEnum


DEFAULT_LOG_FORMAT = "'%(asctime)s %(process)d %(thread)d [CUSTOM] %(levelname)s %(message)s'"
DEFAULT_LOG_FORMAT_DEBUG = "%(asctime)s %(process)d %(thread)d [CUSTOM] %(levelname)s %(message)s"
DEFAULT_LOG_FILE_PATH = "./icon_service_logger"


class LoggerPreset(IntEnum):
    develop = 0
    production = 1


class LogLevel(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


debug_preset = LogConfiguration()
debug_preset.log_format = DEFAULT_LOG_FORMAT_DEBUG
debug_preset.log_level = LogLevel.DEBUG
debug_preset.log_color = True
debug_preset.log_file_path = DEFAULT_LOG_FILE_PATH
debug_preset.set_handler(LogHandlerType.debug)

prod_preset = LogConfiguration()
prod_preset.log_format = DEFAULT_LOG_FORMAT
prod_preset.log_level = LogLevel.DEBUG
prod_preset.log_color = False
prod_preset.log_file_path = DEFAULT_LOG_FILE_PATH
prod_preset.set_handler(LogHandlerType.production)

LogPresets = {LoggerPreset.develop: debug_preset,
              LoggerPreset.production: prod_preset}


class Logger:
    def __init__(self, log_preset: 'LoggerPreset'):
        self.__log_preset = LogPresets[log_preset]
        self.__update_other_loggers()

    def __update_other_loggers(self):
        logger = logging.getLogger('pika')
        self.__log_preset.update_logger(logger)
        logger = logging.getLogger('aio_pika')
        self.__log_preset.update_logger(logger)
        logger = logging.getLogger('sanic.access')
        self.__log_preset.update_logger(logger)

    def set_tag(self, **kwargs):
        self.__log_preset.custom = '_'.join(kwargs.values())
        self.__log_preset.update_logger()

    def set_log_level(self, log_level: 'LogLevel'):
        self.__log_preset.log_level = log_level
        self.__log_preset.update_logger()

    def set_handler_type(self, handler_type: 'LogHandlerType'):
        self.__log_preset.set_handler(handler_type)
        self.__log_preset.update_logger()

    @staticmethod
    def log_info(msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)

    @staticmethod
    def log_debug(msg, *args, **kwargs):
        logging.debug(msg, *args, **kwargs)

    @staticmethod
    def log_warning(msg, *args, **kwargs):
        logging.warning(msg, *args, **kwargs)

    @staticmethod
    def log_exception(msg, *args, exc_info=True, **kwargs):
        logging.exception(msg, *args, exc_info=exc_info, **kwargs)

    @staticmethod
    def log_error(msg, *args, **kwargs):
        logging.error(msg, *args, **kwargs)

