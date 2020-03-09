# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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

import os
import time
from typing import Iterable
from unittest.mock import Mock

import pytest

from iconservice.base.block import Block
from iconservice.base.block import NULL_BLOCK
from iconservice.precommit_data_manager import PrecommitDataManager


class TestPrecommitDataManager(object):
    @pytest.fixture(scope="function")
    def manager(self, create_precommit_data_manager):
        return create_precommit_data_manager(NULL_BLOCK)

    @pytest.fixture(scope="class")
    def create_precommit_data_manager(self):
        def func(block: "Block"):
            manager = PrecommitDataManager()
            manager.init(block)
            return manager

        return func

    @pytest.fixture(scope="function")
    def create_dummy_precommit_data(self):
        def func(block: 'Block'):
            data = Mock()
            data.block_batch.block = block
            return data

        return func

    @staticmethod
    def tx_hash() -> bytes:
        """Returns 32 length random tx_hash in bytes

        :return: tx_hash in bytes
        """
        print("tx_hash()")
        return os.urandom(32)

    @staticmethod
    def block_hash() -> bytes:
        """Returns 32 length random block_hash in bytes

        :return: block_hash in bytes
        """
        print("block_hash()")
        return os.urandom(32)

    @staticmethod
    def timestamp() -> int:
        return int(time.time() * 1_000_000)

    def test_init_with_null_block(self, manager: 'PrecommitDataManager'):
        precommit_data = manager.get(bytes(32))
        assert precommit_data is None

        block: 'Block' = manager.last_block
        assert block == NULL_BLOCK
        assert manager.get(block.hash) is None
        assert len(manager) == 1

    def test_with_genesis_block(self, manager: 'PrecommitDataManager', create_dummy_precommit_data):
        block_hash = bytes(32)
        block = Block(
            block_height=0,
            timestamp=1234,
            block_hash=block_hash,
            prev_hash=None,
        )
        precommit_data = create_dummy_precommit_data(block)

        # TEST: push
        # null_block -> genesis_block
        manager.push(precommit_data)
        assert manager.last_block == NULL_BLOCK
        assert len(manager) == 2

        # TEST: get
        # null_block -> genesis_block
        assert manager.get(block_hash) == precommit_data
        assert len(manager) == 2

        # TEST: commit
        # genesis_block only
        manager.commit(block)
        assert manager.last_block == block
        assert len(manager) == 1

        # TEST clear
        manager.clear()
        assert manager.last_block == block
        assert len(manager) == 1

    def test_get(self, create_precommit_data_manager, create_dummy_precommit_data):
        """
              parent0 - child0
             /
        root - parent1 - child1
             \
              parent2 - child2

        :param create_precommit_data_manager:
        :return:
        """
        block_height = 100
        root = Block(
            block_height=block_height,
            timestamp=self.timestamp(),
            block_hash=self.block_hash(),
            prev_hash=self.block_hash()
        )

        parents = []
        for i in range(3):
            block = Block(
                block_height=root.height + 1,
                timestamp=self.timestamp(),
                block_hash=self.block_hash(),
                prev_hash=root.hash
            )
            parents.append(block)

        children = []
        for i in range(3):
            parent = parents[i]
            block = Block(
                block_height=parent.height + 1,
                prev_hash=parent.hash,
                timestamp=self.timestamp(),
                block_hash=self.block_hash(),
            )
            children.append(block)

        manager = create_precommit_data_manager(root)

        # Push parent blocks
        for block in parents:
            precommit_data = create_dummy_precommit_data(block)
            manager.push(precommit_data)
        assert len(manager) == 4

        # Push child blocks
        for block in children:
            precommit_data = create_dummy_precommit_data(block)
            manager.push(precommit_data)
        assert len(manager) == 7

        # There is no precommit_data for root, because root block has been already committed.
        assert manager.get(root.hash) is None

        for block in parents:
            precommit_data = manager.get(block.hash)
            assert precommit_data.block_batch.block == block

        for block in children:
            precommit_data = manager.get(block.hash)
            assert precommit_data.block_batch.block == block

    def test_push(self, manager):
        pass

    def test_commit(self, manager):
        pass

    def validate_block_to_invoke(self, manager):
        pass

    def validate_block_to_commit(self, manager):
        pass

    def clear(self):
        pass
