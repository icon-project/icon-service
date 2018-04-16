# -*- coding: utf-8 -*-

# Copyright 2018 theloop Inc.
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

import logging


def logd(logger, message: str) -> None:
    if logger:
        logger.debug(message)


def logi(logger, message: str) -> None:
    if logger:
        logger.info(message)


def logw(logger, message: str) -> None:
    if logger:
        logger.debug(message)


def loge(logger, message: str) -> None:
    if logger:
        logger.info(message)


def logf(logger, message: str) -> None:
    if logger:
        logger.fatal(message)


class IcxLogger(object):

    def __init__(self,
                 path: str=None,
                 name: str=None,
                 level: int=logging.DEBUG) -> None:
        """Constructor

        :param path: log file path
        :param name: logger name
        :param level: log level (logging.DEBUG, INFO, WARN, ERROR, FATAL)
        """

        logger = logging.getLogger(name)
        logger.setLevel(level)

        if path:
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            file_handler = logging.FileHandler(path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        self.__logger = logger

    def set_level(self, level: int) -> None:
        self.__logger.setLevel(level)

    def debug(self, message: str) -> None:
        self.__logger.debug(message)

    def info(self, message: str) -> None:
        self.__logger.info(message)

    def warning(self, message: str) -> None:
        self.__logger.warning(message)

    def error(self, message: str) -> None:
        self.__logger.error(message)

    def fatal(self, message: str) -> None:
        self.__logger.fatal(message)
