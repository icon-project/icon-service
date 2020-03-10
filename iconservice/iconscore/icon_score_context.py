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
from abc import ABC
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, List

from iconcommons.logger import Logger

from .icon_score_mapper import IconScoreMapper
from .icon_score_step import IconScoreStepCounter, IconScoreStepCounterFactory
from .icon_score_trace import Trace
from ..base.block import Block
from ..base.exception import FatalException, AccessDeniedException
from ..base.message import Message
from ..base.transaction import Transaction
from ..database.batch import BlockBatch, TransactionBatch
from ..icon_constant import (
    IconScoreContextType, IconScoreFuncType, TERM_PERIOD, PRepGrade, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS,
    Revision, PRepFlag, IconNetworkValueType, RevisionChangedFlag)
from ..icon_network.data.value import Value as IconNetworkValue
from ..icon_network.listener import Listener as INVListener
from ..icx.issue.regulator import Regulator

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_event_log import EventLog

    from ..base.address import Address
    from ..prep.data import PRep, PRepContainer, Term
    from ..utils import ContextEngine, ContextStorage
    from ..icon_network.container import Container as INVContainer


class IconScoreContext(INVListener, ABC):
    TAG = "CTX"

    score_root_path: str = None
    icon_score_mapper: 'IconScoreMapper' = None
    icon_service_flag: int = 0
    legacy_tbears_mode: bool = False
    iiss_initial_irep: int = 0

    engine: 'ContextEngine' = None
    storage: 'ContextStorage' = None

    main_prep_count: int = PREP_MAIN_PREPS
    main_and_sub_prep_count: int = PREP_MAIN_AND_SUB_PREPS
    term_period: int = TERM_PERIOD

    decentralize_trigger: float = 0

    precommitdata_log_flag = False
    step_trace_flag: bool = False
    log_level: str = None

    """Contains the useful information to process user's JSON-RPC request
    """

    def __init__(self, context_type: 'IconScoreContextType' = IconScoreContextType.QUERY) -> None:
        """Constructor

        :param context_type: IconScoreContextType.GENESIS, INVOKE, QUERY
        """
        self.type: 'IconScoreContextType' = context_type
        # The type of external function which is called latest
        self.func_type: 'IconScoreFuncType' = IconScoreFuncType.WRITABLE
        self.block: Optional['Block'] = None
        self.tx: Optional['Transaction'] = None
        self.msg: Optional['Message'] = None
        self.current_address: Optional['Address'] = None
        self.block_batch: Optional['BlockBatch'] = None
        self.tx_batch: Optional['TransactionBatch'] = None
        self.rc_block_batch: list = []
        self.rc_tx_batch: list = []
        self.new_icon_score_mapper: Optional['IconScoreMapper'] = None
        self.cumulative_step_used: int = 0
        self.event_logs: Optional[List['EventLog']] = None
        self.traces: Optional[List['Trace']] = None
        self.fee_sharing_proportion = 0  # The proportion of fee by SCORE in percent (0-100)
        self.step_counter: Optional['IconScoreStepCounter'] = None

        self.msg_stack = []
        self.event_log_stack = []

        # PReps to update on invoke
        self._preps: Optional['PRepContainer'] = None
        self._tx_dirty_preps: Optional[OrderedDict['Address', 'PRep']] = None
        # Collect Main and Sub P-Reps which have just been invalidated by penalty or unregister
        # to use for updating term info at the end of invoke
        self._term: Optional['Term'] = None

        self._inv_container: Optional['INVContainer'] = None

        self.regulator: Optional['Regulator'] = None

        self.revision_changed_flag: 'RevisionChangedFlag' = RevisionChangedFlag.NONE

    @classmethod
    def set_decentralize_trigger(cls, decentralize_trigger: float):
        decentralize_trigger: float = decentralize_trigger

        if not 1.0 > decentralize_trigger >= 0:
            raise FatalException(f"Invalid min delegation percent for decentralize: {decentralize_trigger}."
                                 f"Do not exceed 100% or negative value")
        IconScoreContext.decentralize_trigger = decentralize_trigger

    @property
    def revision(self) -> int:
        if self._inv_container:
            return self._inv_container.revision_code
        else:
            return 0

    @property
    def readonly(self):
        return self.type == IconScoreContextType.QUERY or self.func_type == IconScoreFuncType.READONLY

    @property
    def total_supply(self):
        return self.storage.icx.get_total_supply(self)

    @property
    def preps(self) -> Optional['PRepContainer']:
        return self._preps

    @property
    def term(self) -> Optional['Term']:
        return self._term

    @property
    def inv_container(self) -> Optional['INVContainer']:
        return self._inv_container

    def is_revision_changed(self, target_rev: int) -> bool:
        old: 'INVContainer' = self.engine.inv.inv_container
        new: 'INVContainer' = self.inv_container

        return old.revision_code != new.revision_code and new.revision_code == target_rev

    def is_decentralized(self) -> bool:
        return self._term is not None

    def is_the_first_block_on_decentralization(self) -> bool:
        return self._term.sequence == 0 and self.block.height == self._term.start_block_height

    def set_func_type_by_icon_score(self, icon_score: 'IconScoreBase', func_name: str):
        is_func_readonly = getattr(icon_score, '_IconScoreBase__is_func_readonly')
        if func_name is not None and is_func_readonly(func_name):
            self.func_type = IconScoreFuncType.READONLY
        else:
            self.func_type = IconScoreFuncType.WRITABLE

    # TODO should remove after update GOVERNANCE 0.0.6 afterward
    def deploy(self, tx_hash: bytes) -> None:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        self.engine.deploy.deploy(self, tx_hash)

    def update_batch(self):
        """Called when a transaction is done

        :return:
        """

        # Call update_dirty_prep_batch before update_state_db_batch()
        self.update_dirty_prep_batch()
        self.update_state_db_batch()
        self.update_rc_db_batch()

    def update_state_db_batch(self):
        self.block_batch.update(self.tx_batch)
        self.tx_batch.clear()

    def update_rc_db_batch(self):
        self.rc_block_batch.extend(self.rc_tx_batch)
        self.rc_tx_batch.clear()

    def update_dirty_prep_batch(self):
        """Apply updated P-Rep data to context.preps every time when a tx is done

        Caution: call update_dirty_prep_batch before update_state_db_batch()
        """
        for dirty_prep in self._tx_dirty_preps.values():
            if self._term is not None:
                self._update_term(dirty_prep)

            self._preps.replace(dirty_prep)
            # Write serialized dirty_prep data into tx_batch
            self.storage.prep.put_prep(self, dirty_prep)
            dirty_prep.freeze()

        self._tx_dirty_preps.clear()

    def _update_term(self, dirty_prep: 'PRep'):
        """Update term info with dirty_prep

        :param dirty_prep:
        :return:
        """
        # If dirty_prep address is not contained in term, no need to update self._term
        if dirty_prep.address not in self._term:
            return

        if dirty_prep.is_electable():
            self._change_main_prep_p2p_endpoint(dirty_prep)
        else:
            self._remove_invalid_elected_prep_from_term(dirty_prep)

    def _change_main_prep_p2p_endpoint(self, dirty_prep: 'PRep'):
        """Notify the term that p2p_endpoint of a main P-Rep is changed

        :param dirty_prep: dirty prep
        """
        if self.revision < Revision.REALTIME_P2P_ENDPOINT_UPDATE.value:
            return

        if not self._term.is_main_prep(dirty_prep.address):
            return

        if not dirty_prep.is_flags_on(PRepFlag.P2P_ENDPOINT):
            return

        self._duplicate_term()
        self._term.on_main_prep_p2p_endpoint_changed()

        Logger.info(tag=self.TAG, msg=f"_update_main_prep_endpoint_in_term: {dirty_prep}")

    def _remove_invalid_elected_prep_from_term(self, dirty_prep: 'PRep'):
        """Remove an invalidated elected P-Rep from the current term

        :param dirty_prep: dirty prep
        """
        self._duplicate_term()

        # Just in case, reset the P-Rep grade one to CANDIDATE
        dirty_prep.grade = PRepGrade.CANDIDATE

        self._term.update_invalid_elected_preps([dirty_prep])

        Logger.info(tag=self.TAG, msg=f"Invalid main and sub prep: {dirty_prep}")

    def _duplicate_term(self) -> Optional['Term']:
        if self.type not in (IconScoreContextType.INVOKE, IconScoreContextType.ESTIMATION):
            raise AccessDeniedException(f"Method not allowed: context={self.type.name}")

        if self._term is not None and self._term.is_frozen():
            self._term = self._term.copy()

        return self._term

    def clear_batch(self):
        if self.tx_batch:
            self.tx_batch.clear()
        if self.rc_tx_batch:
            self.rc_tx_batch.clear()
        if self._tx_dirty_preps:
            self._tx_dirty_preps.clear()

    def get_prep(self, address: 'Address', mutable: bool = False) -> Optional['PRep']:
        prep: Optional['PRep'] = None

        if self._tx_dirty_preps is not None:
            prep = self._tx_dirty_preps.get(address)

        if prep is None:
            prep = self._preps.get_by_address(address)

        if prep and prep.is_frozen() and mutable:
            prep = prep.copy()

        return prep

    def put_dirty_prep(self, prep: 'PRep'):
        # Logger.debug(tag=self.TAG, msg=f"put_dirty_prep() start: {prep}")

        if self._tx_dirty_preps is None:
            Logger.warning(tag=self.TAG, msg="self._tx_dirty_preps is None")
            # Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")
            return

        if not prep.is_dirty() and self.revision >= Revision.OPTIMIZE_DIRTY_PREP_UPDATE.value:
            Logger.info(tag=self.TAG, msg=f"No need to update an unchanged P-Rep: revision={self.revision}")
            # Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")
            return

        self._tx_dirty_preps[prep.address] = prep

        # Logger.debug(tag=self.TAG, msg="put_dirty_prep() end")

    def update_icon_network_value(self, value: 'IconNetworkValue'):
        # ICON Network value update listener
        if value.TYPE == IconNetworkValueType.REVISION_CODE:
            pass
        elif value.TYPE == IconNetworkValueType.REVISION_NAME:
            pass
        elif value.TYPE == IconNetworkValueType.SCORE_BLACK_LIST:
            pass
        elif value.TYPE == IconNetworkValueType.STEP_PRICE:
            self.step_counter.set_step_price(value.value)
        elif value.TYPE == IconNetworkValueType.STEP_COSTS:
            self.step_counter.set_step_costs(value.value)
        elif value.TYPE == IconNetworkValueType.MAX_STEP_LIMITS:
            self.step_counter.set_max_step_limit(value.value.get(self.type))
        elif value.TYPE == IconNetworkValueType.SERVICE_CONFIG:
            pass
        elif value.TYPE == IconNetworkValueType.IMPORT_WHITE_LIST:
            pass
        else:
            raise ValueError(f"Invalid value type: {value.TYPE.name}")


class IconScoreContextFactory(object):
    def __init__(self):
        pass

    def create(self, context_type: 'IconScoreContextType', block: 'Block'):
        context: 'IconScoreContext' = self._create_context(context_type)
        context.block = block

        if context_type == IconScoreContextType.DIRECT:
            return context

        self._set_context_attributes_for_processing_tx(context)
        return context

    @classmethod
    def _create_context(cls, context_type: 'IconScoreContextType') -> 'IconScoreContext':
        return IconScoreContext(context_type)

    @classmethod
    def _set_context_attributes_for_processing_tx(cls, context: 'IconScoreContext'):
        if context.type in (IconScoreContextType.INVOKE, IconScoreContextType.ESTIMATION):
            context.block_batch = BlockBatch(Block.from_block(context.block))
            context.tx_batch = TransactionBatch()
            context.new_icon_score_mapper = IconScoreMapper()

            # For PRep management
            context._preps = context.engine.prep.preps.copy(mutable=True)
            context._tx_dirty_preps = OrderedDict()
            container: 'INVContainer' = context.engine.inv.inv_container.copy()
            container.add_listener(context)
            context._inv_container = container
        else:
            # Readonly
            context._preps = context.engine.prep.preps
            context._inv_container = context.engine.inv.inv_container

        cls.set_step_counter(context)
        context._term = context.engine.prep.term

    @classmethod
    def set_step_counter(cls, context: 'IconScoreContext'):
        is_step_trace_on: bool = cls._is_step_trace_on(context)
        if context.type == IconScoreContextType.ESTIMATION:
            context.step_counter = IconScoreStepCounterFactory.create_step_counter(context.inv_container,
                                                                                   IconScoreContextType.INVOKE,
                                                                                   is_step_trace_on)
        else:
            context.step_counter = IconScoreStepCounterFactory.create_step_counter(context.inv_container,
                                                                                   context.type,
                                                                                   is_step_trace_on)

    @classmethod
    def _is_step_trace_on(cls, context: 'IconScoreContext') -> bool:
        return context.step_trace_flag and context.type == IconScoreContextType.INVOKE
