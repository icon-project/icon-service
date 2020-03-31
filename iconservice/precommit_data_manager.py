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

from enum import IntFlag
from typing import TYPE_CHECKING, Optional, List, Dict, Iterable

from iconcommons import Logger

from .base.block import Block, NULL_BLOCK
from .base.exception import InvalidParamsException, InternalServiceErrorException
from .database.batch import BlockBatch
from .database.batch import TransactionBatchValue
from .icon_constant import Revision
from .iconscore.icon_score_mapper import IconScoreMapper
from .iiss.reward_calc.msg_data import TxData
from .prep.prep_address_converter import PRepAddressConverter
from .utils import bytes_to_hex, sha3_256

if TYPE_CHECKING:
    from .base.address import Address
    from .prep.data import PRepContainer, Term


_TAG = "PRECOMMIT"


def _print_block_batch(block_batch: 'BlockBatch') -> List[str]:
    """Print the latest updated states stored in IconServiceEngine
    :return:
    """
    lines = []

    try:
        for i, key in enumerate(block_batch):
            value = block_batch[key]

            if isinstance(value, TransactionBatchValue):
                lines.append(f"{i}: {key.hex()} - {bytes_to_hex(value.value)} - {value.include_state_root_hash}")
            else:
                lines.append(f"{i}: {key.hex()} - {bytes_to_hex(value)}")
    except:
        pass

    return lines


def _print_rc_block_batch(rc_block_batch: list) -> List[str]:
    lines = []

    try:
        tx_index = 0
        for i, data in enumerate(rc_block_batch):
            if isinstance(data, TxData):
                key: bytes = data.make_key(tx_index)
                tx_index += 1
            else:
                key: bytes = data.make_key()

            value: bytes = data.make_value()
            lines.append(f"{i}: {key.hex()} - {value.hex()}")
    except:
        pass

    return lines


class PrecommitFlag(IntFlag):
    # Empty
    NONE = 0x0
    # Set when STEP price changed on the block
    STEP_PRICE_CHANGED = 0x10
    # Set when STEP costs changed on the block
    STEP_COST_CHANGED = 0x20
    # Set when Max STEP limits changed on the block
    STEP_MAX_LIMIT_CHANGED = 0x40
    # STEP changed flag mask
    STEP_ALL_CHANGED = 0xf0
    # CHANGE REVISION
    GENESIS_IISS_CALC = 0x100
    IISS_CALC = 0x200
    DECENTRALIZATION = 0x400


class PrecommitData(object):
    def __init__(self,
                 revision: int,
                 rc_db_revision: int,
                 block_batch: 'BlockBatch',
                 block_result: list,
                 rc_block_batch: list,
                 preps: 'PRepContainer',
                 term: Optional['Term'],
                 prev_block_generator: Optional['Address'],
                 prev_block_validators: Optional[List['Address']],
                 score_mapper: Optional['IconScoreMapper'],
                 precommit_flag: 'PrecommitFlag',
                 rc_state_root_hash: Optional[bytes],
                 added_transactions: dict,
                 main_prep_as_dict: Optional[dict],
                 prep_address_converter: 'PRepAddressConverter'):
        """

        :param block_batch: changed states for a block
        :param block_result: tx_results made from transactions in a block
        :param score_mapper: newly deployed scores in a block
        :param precommit_flag: precommit flag

        """
        self.revision: int = revision
        self.rc_db_revision: int = rc_db_revision
        self.block_batch = block_batch
        self.block_result = block_result
        self.rc_block_batch = rc_block_batch
        # Snapshot of preps
        self.preps = preps
        self.term = term
        self.prev_block_generator = prev_block_generator
        self.prev_block_validators = prev_block_validators
        self.score_mapper = score_mapper
        self.precommit_flag = precommit_flag
        
        self.is_state_root_hash: bytes = self.block_batch.digest()
        self.rc_state_root_hash: Optional[bytes] = rc_state_root_hash

        self.state_root_hash: bytes = self._make_state_root_hash()

        self.added_transactions: dict = added_transactions
        self.main_prep_as_dict: Optional[dict] = main_prep_as_dict

        self.prep_address_converter: 'PRepAddressConverter' = prep_address_converter

        # To prevent redundant precommit data logging
        self.already_exists = False

        # Make preps and term immutable
        if preps:
            preps.freeze()
        if term:
            term.freeze()

    def __str__(self):
        lines = [
            f"revision: {self.revision}",
            f"block: {self.block}",
            f"is_state_root_hash: {bytes_to_hex(self.is_state_root_hash)}",
            f"rc_state_root_hash: {bytes_to_hex(self.rc_state_root_hash)}",
            f"state_root_hash: {bytes_to_hex(self.state_root_hash)}",
            f"prev_block_generator: {self.prev_block_generator}",
            f"precommit_flag: {self.precommit_flag}",
            "",
            f"added_transactions: {self.added_transactions}",
            f"main_prep_as_dict: {self.main_prep_as_dict}",
            "",
            "block_batch",
        ]

        lines.extend(_print_block_batch(self.block_batch))

        lines.append("")
        lines.append("rc_block_batch")
        lines.extend(_print_rc_block_batch(self.rc_block_batch))

        return "\n".join(lines)

    @property
    def block(self) -> Optional['Block']:
        return None if self.block_batch is None else self.block_batch.block

    def _make_state_root_hash(self) -> bytes:
        if self.revision < Revision.DECENTRALIZATION.value or self.rc_state_root_hash is None:
            return self.is_state_root_hash

        data = [self.is_state_root_hash, self.rc_state_root_hash]
        value: bytes = b'|'.join(data)
        return sha3_256(value)


class PrecommitDataManager(object):
    """Manages multiple precommit block data

    Assume that it manages only 2-depth block precommit
    - root: confirmed block: 0-depth
    - root.children (parent): 1-depth
    - parent.children: 2-depth
    """

    class Node(object):
        """Inner class used to manage PrecommitData in LinkedList

        """

        def __init__(
                self, block: 'Block',
                data: 'PrecommitData' = None,
                parent: Optional['PrecommitDataManager.Node'] = None):
            self._block = block
            self._data = data
            self._parent = parent
            self._children: Dict[bytes, 'PrecommitDataManager.Node'] = {}

        @property
        def precommit_data(self) -> 'PrecommitData':
            return self._data

        @property
        def parent(self) -> Optional['PrecommitDataManager.Node']:
            return self._parent

        @parent.setter
        def parent(self, node: Optional['PrecommitDataManager.Node']):
            self._parent = node

        @property
        def block(self) -> 'Block':
            return self._block

        def add_child(self, node: 'PrecommitDataManager.Node'):
            self._children[node.block.hash] = node

        def get_child(self, block_hash: bytes) -> Optional['PrecommitDataManager.Node']:
            return self._children.get(block_hash)

        def children(self) -> Iterable['PrecommitDataManager.Node']:
            for child in self._children.values():
                yield child

        def is_root(self) -> bool:
            return self._parent is None

        def is_leaf(self) -> bool:
            return len(self._children) == 0

    def __init__(self):
        self._root: Optional['PrecommitDataManager.Node'] = None
        # block_hash : PrecommitDataManager.Node instance
        self._precommit_data_mapper: Dict[bytes, 'PrecommitDataManager.Node'] = {}

    def __len__(self):
        return len(self._precommit_data_mapper)

    def init(self, block: Optional['Block']):
        """This is called in IconServiceEngine.open(), IconServiceEngine.rollback() or self._clear()

        :param block: the last confirmed(=committed) block
        :return:
        """
        if not block:
            block = NULL_BLOCK

        self._precommit_data_mapper.clear()

        root = PrecommitDataManager.Node(block)
        self._precommit_data_mapper[root.block.hash] = root
        self._set_root(root)

    @property
    def last_block(self) -> 'Block':
        return self._root.block

    def push(self, precommit_data: 'PrecommitData'):
        block: 'Block' = precommit_data.block_batch.block
        parent: Optional['PrecommitDataManager.Node'] = self._precommit_data_mapper.get(block.prev_hash)

        if parent is None:
            # Genesis block has no prev(=parent) block
            parent = self._root
        elif not (parent and parent.block.height == block.height - 1):
            raise InternalServiceErrorException(
                f"Parent precommitData not found: {bytes_to_hex(block.prev_hash)}")

        node = PrecommitDataManager.Node(block, precommit_data, parent)

        parent.add_child(node)
        self._precommit_data_mapper[block.hash] = node

    def get(self, block_hash: bytes) -> Optional['PrecommitData']:
        if not isinstance(block_hash, bytes):
            return None

        node = self._precommit_data_mapper.get(block_hash)
        return node.precommit_data if node else None

    def commit(self, block: 'Block'):
        node = self._precommit_data_mapper.get(block.hash)
        if node is None:
            Logger.warning(
                tag=_TAG,
                msg=f"No precommit data: height={block.height} hash={bytes_to_hex(block.hash)}")
            return

        if not node.parent.is_root() and self._root == node.parent:
            raise InternalServiceErrorException(f"Parent should be a root")

        self._remove_sibling_precommit_data(block)
        del self._precommit_data_mapper[self._root.block.hash]
        self._set_root(node)

    def _remove_sibling_precommit_data(self, block_to_commit: 'Block'):
        """Remove the sibling blocks whose height is the same as that of the block to commit

        :param block_to_commit:
        :return:
        """
        def pick_up_blocks_to_remove() -> Iterable['PrecommitDataManager.Node']:
            for parent in self._root.children():
                if block_to_commit.hash == parent.block.hash:
                    # DO NOT remove the confirmed block and its children
                    continue

                yield parent
                for child in parent.children():
                    assert parent == child.parent
                    assert child.is_leaf()
                    yield child

        for node_to_remove in pick_up_blocks_to_remove():
            del self._precommit_data_mapper[node_to_remove.block.hash]

    # def remove_precommit_state(self, instant_block_hash: bytes):
    #     if instant_block_hash in self._precommit_data_mapper:
    #         del self._precommit_data_mapper[instant_block_hash]

    def clear(self):
        """Clear all data except for root

        :return:
        """
        self.init(self.last_block)

    def validate_block_to_invoke(self, block: 'Block'):
        """Check if the block to invoke is valid before invoking it

        :param block: block to invoke
        """
        if self._root.block.height < 0:
            # Exception handling for genesis block
            return

        parent: 'PrecommitDataManager.Node' = self._precommit_data_mapper.get(block.prev_hash)
        if parent:
            if block.prev_hash == parent.block.hash and block.height == parent.block.height + 1:
                return

        raise InvalidParamsException(
            f'Failed to invoke a block: '
            f'prev_block({parent.block if parent else None}) '
            f'block_to_invoke({block})')

    def validate_block_to_commit(self, block_hash: bytes):
        """Check block validation
        before write_precommit_state() or remove_precommit_state()
        No need to consider an instant_block_hash on 2-depth block invocation

        :param block_hash: hash data which is used for retrieving block instance from the pre-commit data mapper
        """
        assert isinstance(block_hash, bytes)

        node: 'PrecommitDataManager.Node' = self._precommit_data_mapper.get(block_hash)
        if node is None:
            raise InvalidParamsException(
                f'No precommit data: block_hash={bytes_to_hex(block_hash)}')

        block = node.block
        prev_block = self._root.block

        if block.height == prev_block.height + 1 \
                and (block.height == 0 or node.block.prev_hash == prev_block.hash):
            return

        raise InvalidParamsException(
            f'Invalid precommit block: prev_block({prev_block}) block({block})')

    def _set_root(self, node: 'PrecommitDataManager.Node'):
        node.parent = None
        self._root = node

    def get_block_batches(self, block_hash: bytes) -> Iterable['BlockBatch']:
        node = self._precommit_data_mapper.get(block_hash)
        if not node:
            return

        while not node.is_root():
            yield node.precommit_data.block_batch
            # parent means previous block node
            node = node.parent
