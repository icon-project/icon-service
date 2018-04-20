# Copyright 2017-2018 theloop Inc.
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
""" A class for gRPC service of Icon Service"""

import logging
import setproctitle
import timeit

from loopchain.container import CommonService
from loopchain.protos import loopchain_pb2_grpc, loopchain_pb2
from icon.iconservice import IconOuterService


class IconService(object):
    """IconScore service for stand alone start.
    It provides gRPC interface for peer_service to communicate with icon service.
    Its role is the bridge between loopchain and IconServiceEngine.
    """

    def __init__(self, channel, iconscore_storage_path, peer_target):
        """constructor

        :param channel: (string)
            blockchain channel name.
            A node can have multiple channels.
        :param iconscore_storage_path: (string)
            root path where iconscores are deployed.
            all iconscores have its own folder. (storage_path/contract_address)
        :param peer_target: (string)
            network info of peer_service
            ex: 127.0.0.1:7100
        """

        self.__common_service = CommonService(loopchain_pb2)

        # gRPC service for Score Service
        self.__outer_service = IconOuterService(
            channel, iconscore_storage_path)

        setproctitle.setproctitle(f"{setproctitle.getproctitle()} {channel}")

    @property
    def common_service(self):
        return self.__common_service

    def service_stop(self):
        self.__common_service.stop()

    def serve(self, port):
        """Run grpc server for icon service.

        This function will not return until self.__common_service is over.

        :param port: (int) grpc server port number
        """

        stopwatch_start = timeit.default_timer()

        loopchain_pb2_grpc.add_ContainerServicer_to_server(
            self.__outer_service,
            self.__common_service.outer_server)

        logging.info(f"Start icon service at port: {port}")

        self.__common_service.start(port)

        stopwatch_duration = timeit.default_timer() - stopwatch_start
        logging.info(f"Start icon service start duration({stopwatch_duration})")

        # wait for service termination
        self.__common_service.wait()
