# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
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

__all__ = 'RewardCalcProxy'

import asyncio
import concurrent.futures
import os
from subprocess import Popen
from typing import TYPE_CHECKING, Optional, Callable, Any, Tuple

from iconcommons.logger import Logger
from .message import *
from .message_queue import MessageQueue
from .server import IPCServer
from ....base.address import Address
from ....base.exception import TimeoutException
from ....icon_constant import RCStatus
from ....utils import bytes_to_hex

if TYPE_CHECKING:
    from .message import ReadyNotification, CalculateDoneNotification, NoneResponse

_TAG = "RCP"


class RewardCalcBlock(object):
    """Stores the latest commit status of reward calculator
    """

    def __init__(self, block_height: int, block_hash: bytes):
        self._block_height = block_height
        self._block_hash = block_hash

    @property
    def block_height(self) -> int:
        return self._block_height

    @property
    def block_hash(self) -> bytes:
        return self._block_hash


class RewardCalcProxy(object):
    """Communicates with Reward Calculator through UNIX Domain Socket

    """
    _DEFAULT_REWARD_CALCULATOR_PATH = "icon_rc"

    def __init__(self,
                 icon_rc_path: str,
                 ipc_timeout: int,
                 ready_callback: Callable[['ReadyNotification'], Any] = None,
                 calc_done_callback: Callable[['CalculateDoneNotification'], Any] = None):
        Logger.debug(tag=_TAG, msg="__init__() start")
        Logger.info(tag=_TAG, msg=f"ipc_timeout: {ipc_timeout}")

        self._loop = None
        self._ipc_server = IPCServer()
        self._message_queue: Optional['MessageQueue'] = None
        self._reward_calc: Optional[Popen] = None

        self._ready_future: Optional[asyncio.Future] = None

        self._ready_callback: Optional[Callable] = ready_callback
        self._calculate_done_callback: Optional[Callable] = calc_done_callback
        self._ipc_timeout = ipc_timeout
        self._icon_rc_path = icon_rc_path
        self._rc_block: Optional[RewardCalcBlock] = None

        Logger.debug(tag=_TAG, msg="__init__() end")

    def open(self, log_dir: str, sock_path: str, iiss_db_path: str, icon_rc_monitor: bool):
        Logger.debug(tag=_TAG, msg="open() start")

        self._loop = asyncio.get_event_loop()
        self._message_queue = MessageQueue(loop=self._loop,
                                           notify_message=(VersionResponse, CalculateResponse),
                                           notify_handler=self.notify_handler)
        self._ipc_server.open(self._loop, self._message_queue, sock_path)

        self.start_reward_calc(log_dir=log_dir, sock_path=sock_path, iiss_db_path=iiss_db_path,
                               icon_rc_monitor=icon_rc_monitor)
        self._ready_future = self._loop.create_future()

        Logger.debug(tag=_TAG, msg="open() end")

    def start(self):
        Logger.debug(tag=_TAG, msg="start() end")

        self._ipc_server.start()

        Logger.debug(tag=_TAG, msg="start() end")

    def stop(self):
        Logger.debug(tag=_TAG, msg="stop() start")

        self._stop_message_queue()
        self._ipc_server.stop()

        Logger.debug(tag=_TAG, msg="stop() end")

    def close(self):
        Logger.debug(tag=_TAG, msg="close() start")

        self._ipc_server.close()
        self.stop_reward_calc()

        self._message_queue = None
        self._loop = None
        self._rc_block = None

        Logger.debug(tag=_TAG, msg="close() end")

    def _stop_message_queue(self):
        Logger.info(tag=_TAG, msg="_stop_message_queue() start")

        request = NoneRequest()
        self._message_queue.put(request)

        Logger.info(tag=_TAG, msg="_stop_message_queue() end")

    def is_reward_calculator_ready(self) -> bool:
        return self._ready_future.done()

    def get_version(self):
        Logger.debug(tag=_TAG, msg="get_version() start")

        future: concurrent.futures.Future = \
            asyncio.run_coroutine_threadsafe(self._get_version(), self._loop)

        try:
            response: 'VersionResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("get_version message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg=f"get_version() end: {response.version}")

        return response.version

    async def _get_version(self) -> 'VersionResponse':
        Logger.debug(tag=_TAG, msg="_get_version() start")

        request = VersionRequest()

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_get_version() end")

        return future.result()

    def calculate(self, db_path: str, block_height: int) -> int:
        """Request RewardCalculator to calculate IScore for every account

        It is called on invoke thread

        :param db_path: the absolute path of iiss database
        :param block_height: The blockHeight when this request are sent to RewardCalculator
        """
        Logger.debug(tag=_TAG, msg="calculate() start")

        future: concurrent.futures.Future = \
            asyncio.run_coroutine_threadsafe(self._calculate(db_path, block_height), self._loop)

        try:
            response: 'CalculateResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("calculate message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg=f"calculate() end: {response}")
        return response.status

    async def _calculate(self, db_path: str, block_height: int) -> 'CalculateResponse':
        Logger.debug(tag=_TAG, msg="_calculate() start")

        request = CalculateRequest(db_path, block_height)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg=f"_calculate() end")

        return future.result()

    def claim_iscore(self, address: 'Address',
                     block_height: int, block_hash: bytes,
                     tx_index: int, tx_hash: bytes) -> Tuple[int, int]:
        """Claim IScore of a given address

        It is called on invoke thread

        :param address: the address to claim
        :param block_height: the height of block which contains this claim tx
        :param block_hash: the hash of block which contains this claim tx
        :param tx_index: the index of claimIScore transaction which is contained in a block
        :param tx_hash: the hash of claimIScore transaction
        :return: [i-score(int), block_height(int)]
        :exception TimeoutException: The operation has timed-out
        """
        Logger.debug(
            tag=_TAG,
            msg=f"claim_iscore() start: "
                f"address({address}) block_height({block_height}) block_hash({block_hash.hex()})"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._claim_iscore(address, block_height, block_hash, tx_index, tx_hash), self._loop)

        try:
            response: 'ClaimResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("claim_iscore message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg=f"claim_iscore() end: iscore({response.iscore})")

        return response.iscore, response.block_height

    async def _claim_iscore(self, address: 'Address',
                            block_height: int, block_hash: bytes,
                            tx_index: int, tx_hash: bytes) -> 'ClaimResponse':
        Logger.debug(
            tag=_TAG,
            msg=f"_claim_iscore() start: "
                f"address={address} "
                f"block_height={block_height} "
                f"block_hash={bytes_to_hex(block_hash)} "
                f"tx_index={tx_index} "
                f"tx_hash={bytes_to_hex(tx_hash)}"
        )
        request = ClaimRequest(address, block_height, block_hash, tx_index, tx_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg=f"_claim_iscore() end")

        return future.result()

    def commit_claim(self, success: bool, address: 'Address',
                     block_height: int, block_hash: bytes,
                     tx_index: int, tx_hash: bytes):
        Logger.debug(
            tag=_TAG,
            msg=f"commit_claim() start: "
                f"success={success} "
                f"address={address} "
                f"block_height={block_height} "
                f"block_hash={bytes_to_hex(block_hash)} "
                f"tx_index={tx_index} "
                f"tx_hash={bytes_to_hex(tx_hash)}"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._commit_claim(success, address, block_height, block_hash, tx_index, tx_hash),
            self._loop
        )

        try:
            future.result(self._ipc_timeout)

        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("COMMIT_CLAIM message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg="commit_claim() end")

    async def _commit_claim(self, success: bool, address: 'Address',
                            block_height: int, block_hash: bytes,
                            tx_index: int, tx_hash: bytes) -> 'CommitClaimResponse':
        Logger.debug(
            tag=_TAG,
            msg=f"_commit_claim() start: "
                f"success={success} "
                f"address={address} "
                f"block_height={block_height} "
                f"block_hash={bytes_to_hex(block_hash)} "
                f"tx_index={tx_index} "
                f"tx_hash={bytes_to_hex(tx_hash)}"
        )

        request = CommitClaimRequest(success, address, block_height, block_hash, tx_index, tx_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_commit_claim() end")

        return future.result()

    def query_iscore(self, address: 'Address') -> Tuple[int, int]:
        """Returns the I-Score of a given address

        It should be called on query thread

        :param address: the address to query
        :return: [i-score(int), block_height(int)]
        :exception TimeoutException: The operation has timed-out
        """
        assert isinstance(address, Address)

        Logger.debug(tag=_TAG, msg="query_iscore() start")

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._query_iscore(address), self._loop)

        try:
            response: 'QueryResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("query_iscore message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg="query_iscore() end")

        return response.iscore, response.block_height

    async def _query_iscore(self, address: 'Address') -> 'QueryResponse':
        """

        :param address:
        :return: [iscore(int), block_height(int)]
        """
        Logger.debug(tag=_TAG, msg="_query_iscore() start")

        request = QueryRequest(address)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_query_iscore() end")

        return future.result()

    def query_calculate_status(self) -> tuple:
        Logger.debug(tag=_TAG, msg="query_calculate_status() start")

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._query_calculate_status(), self._loop)

        try:
            response: QueryCalculateStatusResponse = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("query_calculate_status message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg="query_calculate_status() end")

        return response.status, response.block_height

    async def _query_calculate_status(self) -> 'QueryCalculateStatusResponse':
        Logger.debug(tag=_TAG, msg="_query_calculate_status() start")

        request = QueryCalculateStatusRequest()

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_query_calculate_status() end")

        return future.result()

    def query_calculate_result(self, block_height) -> tuple:
        Logger.debug(tag=_TAG, msg="query_calculate_result() start")

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._query_calculate_result(block_height), self._loop)

        try:
            response: QueryCalculateResultResponse = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("query_calculate_result message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg="query_calculate_result() end")

        return response.status, response.block_height, response.iscore, response.state_hash

    async def _query_calculate_result(self, block_height) -> 'QueryCalculateResultResponse':
        Logger.debug(tag=_TAG, msg="_query_calculate_result() start")

        request = QueryCalculateResultRequest(block_height)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_query_calculate_result() end")

        return future.result()

    def commit_block(self, success: bool, block_height: int, block_hash: bytes) -> tuple:
        """Notify reward calculator of block confirmation

        It is called on invoke thread

        :param success: true for success, false for failure
        :param block_height: the height of block
        :param block_hash: the hash of block
        :return: [success(bool), block_height(int), block_hash(bytes)]
        :exception TimeoutException: The operation has timed-out
        """
        Logger.debug(
            tag=_TAG,
            msg=f"commit_block() start: success={success}, "
                f"block_height={block_height}, "
                f"block_hash={bytes_to_hex(block_hash)}"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._commit_block(success, block_height, block_hash), self._loop)

        try:
            response: 'CommitBlockResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("commit_block message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg=f"commit_block() end. response: {response}")

        return response.success, response.block_height, response.block_hash

    async def _commit_block(self, success: bool, block_height: int, block_hash: bytes) -> 'CommitBlockResponse':
        # Logger.debug(tag=_TAG, msg="_commit_block() start")

        request = CommitBlockRequest(success, block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        # Logger.debug(tag=_TAG, msg="_commit_block() end")

        return future.result()

    def init_reward_calculator(self, block_height: int) -> int:
        Logger.debug(tag=_TAG, msg=f"init_reward_calculator() start: block_height={block_height}")

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._init_reward_calculator(block_height), self._loop)

        try:
            response: InitResponse = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("query_calculate_result message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg="query_calculate_result() end")

        return response.success

    async def _init_reward_calculator(self, block_height: int):
        Logger.debug(tag=_TAG, msg=f"init_reward_calculator() start: block_height={block_height}")

        request = InitRequest(block_height)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="init_reward_calculator() end")

        return future.result()

    def rollback(self, block_height: int, block_hash: bytes) -> Tuple[bool, int, bytes]:
        """Request reward calculator to rollback the DB of the reward calculator to the specific block height.

        Reward calculator DOES NOT process other messages while processing ROLLBACK message

        :param block_height:
        :param block_hash:
        :return:
        """

        Logger.debug(
            tag=_TAG,
            msg=f"rollback() start: block_height={block_height}, block_hash={bytes_to_hex(block_hash)}"
        )

        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(
            self._rollback(block_height, block_hash), self._loop)

        try:
            response: 'RollbackResponse' = future.result(self._ipc_timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutException("rollback message to RewardCalculator has timed-out")

        Logger.debug(tag=_TAG, msg=f"rollback() end. response: {response}")

        return response.success, response.block_height, response.block_hash

    async def _rollback(self, block_height: int, block_hash: bytes) -> 'RollbackResponse':
        Logger.debug(tag=_TAG, msg="_rollback() start")

        request = RollbackRequest(block_height, block_hash)

        future: asyncio.Future = self._message_queue.put(request)
        await future

        Logger.debug(tag=_TAG, msg="_rollback() end")

        return future.result()

    def ready_handler(self, response: 'ReadyNotification'):
        Logger.debug(tag=_TAG, msg=f"ready_handler() start {response}")

        if self._ready_callback is not None:
            self._ready_callback(response)

        self._ready_future.set_result(RCStatus.READY)
        self._rc_block = RewardCalcBlock(response.block_height, response.block_height)

    def get_ready_future(self):
        return self._ready_future

    def calculate_done_handler(self, response: 'Response'):
        Logger.debug(tag=_TAG, msg=f"calculate_done_handler() start {response}")
        if self._calculate_done_callback is not None:
            self._calculate_done_callback(response)

    def notify_handler(self, response: 'Response'):
        Logger.debug(tag=_TAG, msg=f"notify_handler() start {type(response)}")
        if isinstance(response, ReadyNotification):
            self.ready_handler(response=response)
        elif isinstance(response, CalculateDoneNotification):
            self.calculate_done_handler(response=response)

    def start_reward_calc(self, log_dir: str, sock_path: str, iiss_db_path: str, icon_rc_monitor: bool):
        """ Start reward calculator process

        :param log_dir: log directory
        :param sock_path: unix domain socket path for IPC
        :param iiss_db_path: IISS data DB path
        :param icon_rc_monitor: Boolean which determines Opening RC monitor channel (default True)
        :return: void
        """
        Logger.debug(tag=_TAG, msg=f'run reward calc')

        iscore_db_path, _ = os.path.split(iiss_db_path)
        iscore_db_path = os.path.join(iscore_db_path, 'rc')
        log_path = os.path.join(log_dir, 'rc.log')
        reward_calculator_path: str = self._get_reward_calculator_path(self._icon_rc_path)

        if self._reward_calc is None:
            args = [
                reward_calculator_path,
                "-client",
                "-db-count", "16",
                "-db", f"{iscore_db_path}",
                "-iissdata", f"{iiss_db_path}",
                "-ipc-addr", f"{sock_path}",
                "-log-file", f"{log_path}",
            ]
            if icon_rc_monitor is True:
                args.append("-monitor")

            Logger.info(tag=_TAG, msg=f"cmd={' '.join(args)}")
            self._reward_calc = Popen(args)

        Logger.debug(tag=_TAG, msg="start_reward_calc() end")

    def _get_reward_calculator_path(self, path: str) -> str:
        command = self._DEFAULT_REWARD_CALCULATOR_PATH

        if isinstance(path, str):
            if os.path.isdir(path):
                return os.path.join(path, command)
            elif os.path.isfile(path):
                return path

        return command

    def stop_reward_calc(self):
        """ Stop reward calculator process

        :return: void
        """
        Logger.debug(tag=_TAG, msg='stop reward calc')

        if self._reward_calc is not None:
            self._reward_calc.kill()
            self._reward_calc = None

    def get_commit_block(self) -> Optional[Tuple[int, bytes]]:
        if self._rc_block is None:
            return None

        return self._rc_block.block_height, self._rc_block.block_hash
