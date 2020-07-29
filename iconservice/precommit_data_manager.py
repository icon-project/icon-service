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
import json
import os
from typing import TYPE_CHECKING, Optional, List, Dict, Iterable

from iconcommons import Logger

from .base.block import Block, NULL_BLOCK
from .base.exception import InvalidParamsException, InternalServiceErrorException
from .database.batch import BlockBatch
from .icon_constant import Revision
from .iconscore.icon_score_mapper import IconScoreMapper
from .iiss.reward_calc.msg_data import TxData
from .inv.container import Container as INVContainer
from .prep.prep_address_converter import PRepAddressConverter
from .utils import bytes_to_hex, sha3_256, to_camel_case
from . import __version__

if TYPE_CHECKING:
    from .base.address import Address
    from .prep.data import PRepContainer, Term

_TAG = "PRECOMMIT"


class PrecommitDataWriter:
    """
    Write Precommit data to the file for debugging
    """
    VERSION = 0
    DIR_NAME = "precommit"

    def __init__(self, path: str):
        self._dir_path: str = os.path.join(path, self.DIR_NAME)
        if not os.path.exists(self._dir_path):
            os.makedirs(self._dir_path)
        self._filename_suffix = f"precommit-v{self.VERSION}.json"

    def write(self, precommit_data: 'PrecommitData'):
        """
            Write the human readable precommit data to the file for debugging
            :param precommit_data:
            :param path: path to record
            :return:
            """
        filename: str = f"{precommit_data.block.height}" \
                        f"-{precommit_data.state_root_hash.hex()[:8]}" \
                        f"-{self._filename_suffix}"
        Logger.info(
            tag=_TAG,
            msg=f"PrecommitDataWriter.write() start (precommit: {precommit_data})"
        )
        with open(os.path.join(self._dir_path, filename), 'w') as f:
            try:
                block = precommit_data.block
                json_dict = {
                    "iconservice": __version__,
                    "revision": precommit_data.revision,
                    "block": block.to_dict(to_camel_case) if block is not None else None,
                    "isStateRootHash": precommit_data.is_state_root_hash,
                    "rcStateRootHash": precommit_data.rc_state_root_hash,
                    "stateRootHash": precommit_data.state_root_hash,
                    "prevBlockGenerator": precommit_data.prev_block_generator,
                    "blockBatch": precommit_data.block_batch.to_list(),
                    "rcBlockBatch": self._convert_rc_block_batch_to_list(precommit_data.rc_block_batch)
                }
                json.dump(json_dict, f, default=self._json_default)
            except Exception as e:
                Logger.exception(
                    tag=_TAG,
                    msg=f"Exception raised during writing the precommit-data: {e}"
                )
        Logger.info(
            tag=_TAG,
            msg=f"PrecommitDataWriter.write() end"
        )

    @classmethod
    def _json_default(cls, obj):
        # json package do not  Address obj
        from iconservice import Address

        if isinstance(obj, bytes):
            return bytes_to_hex(obj)
        elif isinstance(obj, Address):
            return str(obj)
        return obj

    @classmethod
    def _convert_rc_block_batch_to_list(cls, rc_block_batch: list):
        new_list = []
        tx_index = 0
        for data in rc_block_batch:
            if isinstance(data, TxData):
                key: bytes = data.make_key(tx_index)
                tx_index += 1
            else:
                key: bytes = data.make_key()

            value: bytes = data.make_value()
            new_list.append({
                "key": key,
                "value": value
            })
        return new_list


class PrecommitData(object):
    def __init__(self,
                 revision: int,
                 rc_db_revision: int,
                 inv_container: 'INVContainer',
                 block_batch: 'BlockBatch',
                 block_result: list,
                 rc_block_batch: list,
                 preps: 'PRepContainer',
                 term: Optional['Term'],
                 prev_block_generator: Optional['Address'],
                 prev_block_validators: Optional[List['Address']],
                 score_mapper: Optional['IconScoreMapper'],
                 rc_state_root_hash: Optional[bytes],
                 added_transactions: dict,
                 next_preps: Optional[dict],
                 prep_address_converter: 'PRepAddressConverter'):
        """

        :param block_batch: changed states for a block
        :param block_result: tx_results made from transactions in a block
        :param score_mapper: newly deployed scores in a block

        """
        # Todo: check if remove the revision
        self.revision: int = revision
        self.rc_db_revision: int = rc_db_revision
        self.inv_container: 'INVContainer' = inv_container
        self.block_batch = block_batch
        self.block_result = block_result
        self.rc_block_batch = rc_block_batch
        # Snapshot of preps
        self.preps = preps
        self.term = term
        self.prev_block_generator = prev_block_generator
        self.prev_block_validators = prev_block_validators
        self.score_mapper = score_mapper

        self.is_state_root_hash: bytes = self.block_batch.digest()
        self.rc_state_root_hash: Optional[bytes] = rc_state_root_hash

        self.state_root_hash: bytes = self._make_state_root_hash()

        self.added_transactions: dict = added_transactions
        self.next_preps: Optional[dict] = next_preps

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
            f"added_transactions: {self.added_transactions}",
            f"next_preps: {self.next_preps}"
        ]
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

        def update_block_hash(self, block_hash: bytes):
            self.precommit_data.block_batch.update_block_hash(block_hash)
            self._block = self.precommit_data.block_batch.block

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

    def change_block_hash(self, block_height: int, src: bytes, dst: bytes):
        node: 'PrecommitDataManager.Node' = self._precommit_data_mapper.get(src)
        if node is None:
            raise InvalidParamsException(
                f'No precommit data: block_hash={bytes_to_hex(src)}')

        if not node.is_leaf() or node.block.height != block_height:
            raise InvalidParamsException(
                f"Invalid node data (not leaf): src={src}, dest={dst}")

        node.update_block_hash(block_hash=dst)
        del self._precommit_data_mapper[src]
        self._precommit_data_mapper[dst] = node
