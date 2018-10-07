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
import warnings

import threading
from typing import TYPE_CHECKING, Optional, List, Tuple

from .icon_score_trace import Trace
from .internal_call import InternalCall
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.block import Block
from ..base.exception import ServerErrorException, InvalidParamsException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import IconScoreContextType, IconScoreFuncType, DEFAULT_BYTE_SIZE, IconServiceFlag

if TYPE_CHECKING:
    from .icon_score_mapper import IconScoreMapper
    from .icon_score_step import IconScoreStepCounter
    from .icon_score_event_log import EventLog
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine
    from .icon_score_base import IconScoreBase
    from ..base.address import Address

_thread_local_data = threading.local()


class ContextContainer(object):
    """ContextContainer mixin

    Every class which inherits ContextContainer can share IconScoreContext instance
    in the current thread.
    """

    @staticmethod
    def _get_context() -> Optional['IconScoreContext']:
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack[-1]
        else:
            return None

    @staticmethod
    def _push_context(context: 'IconScoreContext') -> None:
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is None:
            context_stack = []
            setattr(_thread_local_data, 'context_stack', context_stack)

        context_stack.append(context)

    @staticmethod
    def _pop_context() -> 'IconScoreContext':
        """Delete the last pushed context of the current thread
        """
        context_stack: List['IconScoreContext'] \
            = getattr(_thread_local_data, 'context_stack', None)

        if context_stack is not None and len(context_stack) > 0:
            return context_stack.pop()
        else:
            raise ServerErrorException('Failed to pop a context out of context_stack')

    @staticmethod
    def _clear_context() -> None:
        setattr(_thread_local_data, 'context_stack', None)


class ContextGetter(object):
    """The class which refers to IconScoreContext should inherit ContextGetter
    """

    @property
    def _context(self) -> 'IconScoreContext':
        return ContextContainer._get_context()


class IconScoreContext(object):
    """Contains the useful information to process user's jsonrpc request
    """
    icon_score_mapper: 'IconScoreMapper' = None
    icon_score_deploy_engine: 'IconScoreDeployEngine'
    icon_service_flag: int = 0
    legacy_tbears_mode = False

    def __init__(self,
                 context_type: 'IconScoreContextType' = IconScoreContextType.QUERY,
                 func_type: 'IconScoreFuncType' = IconScoreFuncType.WRITABLE,
                 block: 'Block' = None,
                 tx: 'Transaction' = None,
                 msg: 'Message' = None,
                 block_batch: 'BlockBatch' = None,
                 tx_batch: 'TransactionBatch' = None,
                 new_icon_score_mapper: 'IconScoreMapper' = None) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        :param func_type: IconScoreFuncType (READONLY, WRITABLE)
        :param block:
        :param tx: initial transaction info
        :param msg: message call info
        :param block_batch:
        :param tx_batch:
        """
        self.type: IconScoreContextType = context_type
        # The type of external function which is called latest
        self.func_type: IconScoreFuncType = func_type
        self.block = block
        self.tx = tx
        self.msg = msg
        self.current_address: Address = None
        self.block_batch = block_batch
        self.tx_batch = tx_batch
        self.new_icon_score_mapper = new_icon_score_mapper
        self.cumulative_step_used: int = 0
        self.step_counter: 'IconScoreStepCounter' = None
        self.event_logs: List['EventLog'] = None
        self.traces: List['Trace'] = None

        self.internal_call = InternalCall(self)
        self.msg_stack = []
        self.event_log_stack = []

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY or \
               self.func_type == IconScoreFuncType.READONLY

    def clear(self) -> None:
        """Set instance member variables to None
        """
        self.block = None
        self.tx = None
        self.msg = None
        self.block_batch = None
        self.tx_batch = None
        self.new_icon_score_mapper = None
        self.cumulative_step_used = 0
        self.step_counter = None
        self.event_logs = None
        self.traces = None
        self.func_type = IconScoreFuncType.WRITABLE

        self.msg_stack.clear()
        self.event_log_stack.clear()

    def is_score_active(self,
                        context: Optional['IconScoreContext'],
                        icon_score_address: 'Address') -> bool:
        return self.icon_score_deploy_engine.icon_deploy_storage.is_score_active(context, icon_score_address)

    def get_owner(self,
                  context: Optional['IconScoreContext'],
                  icon_score_address: 'Address') -> Optional['Address']:
        return self.icon_score_deploy_engine.icon_deploy_storage.get_score_owner(context, icon_score_address)

    def deploy(self, tx_hash: bytes) -> None:
        self.icon_score_deploy_engine.deploy(self, tx_hash)

    def get_icon_score(self, address: 'Address') -> Optional['IconScoreBase']:
        score = None

        if self.type == IconScoreContextType.INVOKE:
            if self.new_icon_score_mapper is not None:
                score = self.new_icon_score_mapper.get(address)
        if score is None:
            score = self._get_icon_score(address)

        return score

    def _get_icon_score(self, address: 'Address') -> Optional['IconScoreBase']:
        is_score_active = self.icon_score_deploy_engine.icon_deploy_storage.is_score_active(self, address)

        if not is_score_active:
            raise InvalidParamsException(f'SCORE is inactive: {address}')

        deploy_info = self.icon_score_deploy_engine.icon_deploy_storage.get_deploy_info(self, address)
        if deploy_info is None:
            current_tx_hash = None
        else:
            current_tx_hash = deploy_info.current_tx_hash

        if current_tx_hash is None:
            current_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        return self.icon_score_mapper.get_icon_score(address, current_tx_hash)

    def try_score_package_validate(self, address: 'Address', tx_hash: bytes):
        self.icon_score_mapper.try_score_package_validate(address, tx_hash)

    def validate_score_blacklist(self, score_address: 'Address'):
        """Prevent SCOREs in blacklist

        :param score_address:
        """
        if not score_address.is_contract:
            raise ServerErrorException(f'Invalid SCORE address: {score_address}')

        # Gets the governance SCORE
        governance_score: 'Governance' = self.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        if governance_score.isInScoreBlackList(score_address):
            raise ServerErrorException(f'SCORE in blacklist: {score_address}')

    def validate_deployer(self, deployer: 'Address'):
        """Check if a given deployer is allowed to deploy a SCORE

        :param deployer: EOA address to deploy a SCORE
        """
        # Gets the governance SCORE
        governance_score: 'Governance' = self.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        if not governance_score.isDeployer(deployer):
            raise ServerErrorException(f'Invalid deployer: no permission (address: {deployer})')

    def is_service_flag_on(self, flag: 'IconServiceFlag'):
        service_flag = self._get_service_flag()
        return self._is_flag_on(service_flag, flag)

    @staticmethod
    def _is_flag_on(src_flag: int, dst_flag: int):
        return src_flag & dst_flag == dst_flag

    def _get_service_flag(self) -> int:
        governance_score = self.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        service_config = self.icon_service_flag
        try:
            service_config = governance_score.service_config
        except AttributeError:
            pass
        return service_config

    def get_revision(self) -> int:
        try:
            governance_score = self.get_icon_score(GOVERNANCE_SCORE_ADDRESS)
            if governance_score is not None:
                if hasattr(governance_score, 'revision_code'):
                    return governance_score.revision_code
        except:
            pass

        return 0

    def get_tx_hashes_by_score_address(self,
                                       context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return self.icon_score_deploy_engine.icon_deploy_storage.get_tx_hashes_by_score_address(context, score_address)

    def get_score_address_by_tx_hash(self,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return self.icon_score_deploy_engine.icon_deploy_storage.get_score_address_by_tx_hash(context, tx_hash)

    def enter_call(self):
        """Start to call external function provided by other SCORE
        """
        if self.type != IconScoreContextType.INVOKE:
            return

        self.tx_batch.enter_call()

        self.event_log_stack.append(self.event_logs)
        self.event_logs = []

    def revert_call(self):
        """An exception happens during calling an external function provided by other SCORE
        Revert the states changed by this function call
        """
        if self.type != IconScoreContextType.INVOKE:
            return

        self.tx_batch.revert_call()

        self.event_logs.clear()

    def leave_call(self):
        """Finish to call external function provided by other SCORE
        """
        if self.type != IconScoreContextType.INVOKE:
            return

        self.tx_batch.leave_call()

        prev_event_logs = self.event_log_stack.pop()
        self.event_logs = prev_event_logs + self.event_logs


class IconScoreContextFactory(object):
    """IconScoreContextFactory
    """

    def __init__(self, max_size: int) -> None:
        """Constructor
        """
        self._lock = threading.Lock()
        self._queue = []
        self._max_size = max_size

    def create(self,
               context_type: 'IconScoreContextType') -> 'IconScoreContext':
        with self._lock:
            if len(self._queue) > 0:
                context = self._queue.pop()
                context.type = context_type
            else:
                context = IconScoreContext(context_type)

        return context

    def destroy(self, context: 'IconScoreContext') -> None:
        with self._lock:
            if len(self._queue) < self._max_size:
                context.clear()
                self._queue.append(context)
