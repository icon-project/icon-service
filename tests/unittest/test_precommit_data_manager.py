import os
import shutil
from unittest.mock import Mock

import pytest

from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue
from iconservice.precommit_data_manager import PrecommitData, write_precommit_data_to_file
from tests import create_hash_256

PRECOMMIT_LOG_PATH = "precommit"


@pytest.fixture
def block_batch():
    block = Mock(spec=Block)
    block.height = 1
    block_batch: 'BlockBatch' = BlockBatch(Mock(spec=Block))
    tx_batch: 'TransactionBatch' = TransactionBatch()

    block_batch.block = block
    for i in range(3):
        tx_batch[create_hash_256()] = TransactionBatchValue(create_hash_256(), True, i)
    block_batch.update(tx_batch)

    return block_batch


@pytest.fixture
def precommit_data(block_batch):
    precommit_data: 'PrecommitData' = Mock(spec=PrecommitData)
    precommit_data.block = block_batch.block
    precommit_data.block_batch = block_batch
    precommit_data.rc_block_batch = []
    return precommit_data


def teardown_function():
    shutil.rmtree(PRECOMMIT_LOG_PATH, ignore_errors=True)


def test_write_precommit_data(precommit_data):
    expected_file_name: str = f"{precommit_data.block.height}-precommit-data.txt"

    write_precommit_data_to_file(precommit_data, "")

    assert os.path.exists(PRECOMMIT_LOG_PATH)
    assert os.path.exists(os.path.join(PRECOMMIT_LOG_PATH, expected_file_name))


def test_write_precommit_data_when_raising_exception_should_print_exception(precommit_data):
    expected_file_name: str = f"{precommit_data.block.height}-precommit-data.txt"
    # Set the invalid data to rc block batch (it is going to be a reason of the exception)
    precommit_data.rc_block_batch.append("invalid data")

    # Act
    write_precommit_data_to_file(precommit_data, "")

    assert os.path.exists(PRECOMMIT_LOG_PATH)
    assert os.path.exists(os.path.join(PRECOMMIT_LOG_PATH, expected_file_name))
