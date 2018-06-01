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

DEFAULT_LOG_FORMAT = "%(asctime)s %(process)d %(thread)d %(levelname)s %(message)s"
DEFAULT_LOG_FILE_PATH = "./logger.log"

DEFAULT_LOG_TAG = "LOG"


class LogLevel(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Logger:
    def __init__(self, import_file_path: str = None):
        if import_file_path is None:
            self.__log_preset = Logger.__make_default_preset()
        else:
            self.__log_preset = Logger.import_file(import_file_path)

        self.update_other_logger_level('pika', True)
        self.update_other_logger_level('aio_pika', True)
        self.update_other_logger_level('sanic.access', True)
        self.__log_preset.update_logger()

    @staticmethod
    def import_file(path: str):
        try:
            with open(path) as f:
                conf = json.load(f)
                logger_config = conf["log"]
                return Logger.import_dict(logger_config)
        except Exception:
            return Logger.__make_default_preset()

    @staticmethod
    def import_dict(conf: dict):
        log_format = conf.get("format", DEFAULT_LOG_FORMAT)
        log_level = conf.get("level", LogLevel.DEBUG)
        log_color = conf.get("colorLog", True)
        log_output = conf.get('filePath', DEFAULT_LOG_FILE_PATH)
        log_output_type_str = conf.get('outputType', 'debug')

        preset = LogConfiguration()
        preset.log_format = log_format
        preset.log_level = log_level
        preset.log_color = log_color
        preset.log_file_path = log_output
        preset.set_handler(LogHandlerType[log_output_type_str])
        return preset

    @staticmethod
    def __make_default_preset():
        preset = LogConfiguration()
        preset.log_format = DEFAULT_LOG_FORMAT
        preset.log_level = LogLevel.DEBUG
        preset.log_color = True
        preset.log_file_path = DEFAULT_LOG_FILE_PATH
        preset.set_handler(LogHandlerType.CONSOLE|LogHandlerType.FILE)
        return preset

    def update_other_logger_level(self, logger_name: str, disable: bool = False):
        logger = logging.getLogger(logger_name)
        if logger is not None:
            self.__log_preset.update_logger(logger, disable)

    def set_log_level(self, log_level: 'LogLevel'):
        self.__log_preset.log_level = log_level
        self.__log_preset.update_logger()

    def set_handler_type(self, handler_type: 'LogHandlerType'):
        self.__log_preset.set_handler(handler_type)
        self.__log_preset.update_logger()

    @staticmethod
    def debug(msg: str, tag: str = DEFAULT_LOG_TAG):
        logging.debug(Logger.__make_log_msg(msg, tag))

    @staticmethod
    def info(msg: str, tag: str = DEFAULT_LOG_TAG):
        logging.info(Logger.__make_log_msg(msg, tag))

    @staticmethod
    def warning(msg: str, tag: str = DEFAULT_LOG_TAG):
        logging.warning(Logger.__make_log_msg(msg, tag))

    @staticmethod
    def error(msg: str, tag: str = DEFAULT_LOG_TAG):
        logging.error(Logger.__make_log_msg(msg, tag))

    @staticmethod
    def exception(msg, tag: str = DEFAULT_LOG_TAG):
        logging.exception(Logger.__make_log_msg(msg, tag), exc_info=True)

    @staticmethod
    def __make_log_msg(msg: str, tag: str):
        return f'[{tag}]{msg}'
