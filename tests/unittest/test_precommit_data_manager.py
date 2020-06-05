import json
import os
import shutil
from unittest.mock import Mock

import pytest

from iconservice import __version__, Address
from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch, TransactionBatchValue
from iconservice.iiss.reward_calc.msg_data import TxData, TxType, PRepRegisterTx, GovernanceVariable
from iconservice.precommit_data_manager import PrecommitData, PrecommitDataWriter
from iconservice.utils import bytes_to_hex
from tests import create_hash_256, create_timestamp, create_block_hash, create_address
from tests.unittest.iiss.test_reward_calc_data_storage import DUMMY_BLOCK_HEIGHT, CONFIG_MAIN_PREP_COUNT, \
    CONFIG_SUB_PREP_COUNT

PRECOMMIT_LOG_PATH = os.path.join(os.getcwd(), PrecommitDataWriter.DIR_NAME)

DATA_LIST = [1, b'bytes', 'string', create_address(), True, None]


@pytest.fixture
def block_batch():
    block = Block(block_height=1,
                  block_hash=create_block_hash(),
                  timestamp=create_timestamp(),
                  prev_hash=create_block_hash(),
                  cumulative_fee=5)
    block_batch: 'BlockBatch' = BlockBatch(block)
    block_batch.block = block
    tx_batch: 'TransactionBatch' = TransactionBatch()

    for i, data in enumerate(DATA_LIST):
        tx_batch[create_hash_256()] = TransactionBatchValue(data, True, i)
    block_batch.update(tx_batch)

    return block_batch


@pytest.fixture
def rc_block_batch():
    rc_block_batch: list = []
    gv = GovernanceVariable()
    gv.block_height = DUMMY_BLOCK_HEIGHT
    gv.config_main_prep_count = CONFIG_MAIN_PREP_COUNT
    gv.config_sub_prep_count = CONFIG_SUB_PREP_COUNT
    gv.calculated_irep = 1
    gv.reward_rep = 1000
    rc_block_batch.append(gv)
    for i in range(2):
        tx = TxData()
        tx.address = create_address()
        tx.block_height = DUMMY_BLOCK_HEIGHT
        tx.type = TxType.PREP_REGISTER
        tx.data = PRepRegisterTx()
        rc_block_batch.append(tx)
    return rc_block_batch


@pytest.fixture
def precommit_data(block_batch, rc_block_batch):
    precommit_data: 'PrecommitData' = Mock(spec=PrecommitData)
    precommit_data.block = block_batch.block
    precommit_data.revision = 1
    precommit_data.is_state_root_hash = create_hash_256()
    precommit_data.rc_state_root_hash = None
    precommit_data.state_root_hash = create_hash_256()
    precommit_data.prev_block_generator = create_address()
    precommit_data.block_batch = block_batch
    precommit_data.rc_block_batch = rc_block_batch
    return precommit_data


@pytest.fixture
def expected_json_data(precommit_data):
    def expected_encoder(data):
        if isinstance(data, bytes):
            return bytes_to_hex(data)
        elif isinstance(data, Address):
            return str(data)
        return data

    block = precommit_data.block

    json_dict = {
        "iconservice": __version__,
        "revision": precommit_data.revision,
        "block": {
            "height": block.height,
            "hash": bytes_to_hex(block.hash),
            "timestamp": block.timestamp,
            "prevHash": bytes_to_hex(block.prev_hash),
            "cumulativeFee": block.cumulative_fee
        },
        "isStateRootHash": bytes_to_hex(precommit_data.is_state_root_hash),
        "rcStateRootHash": None,
        "stateRootHash": bytes_to_hex(precommit_data.state_root_hash),
        "prevBlockGenerator": str(precommit_data.prev_block_generator),
        "blockBatch": [
            {"key": bytes_to_hex(k),
             "value": expected_encoder(v.value),
             "includeStateRootHash": v.include_state_root_hash,
             "txIndexes": v.tx_indexes}
            for k, v in precommit_data.block_batch.items()
        ],
        "rcBlockBatch": [
            {
                "key": bytes_to_hex(precommit_data.rc_block_batch[0].make_key()),
                "value": bytes_to_hex(precommit_data.rc_block_batch[0].make_value())
            },
            {
                "key": bytes_to_hex(precommit_data.rc_block_batch[1].make_key(0)),
                "value": bytes_to_hex(precommit_data.rc_block_batch[1].make_value())
            },
            {
                "key": bytes_to_hex(precommit_data.rc_block_batch[2].make_key(1)),
                "value": bytes_to_hex(precommit_data.rc_block_batch[2].make_value())
            }
        ]
    }
    return json_dict


def teardown_function():
    shutil.rmtree(PRECOMMIT_LOG_PATH, ignore_errors=True)


def test_precommit_data_dir_and_file_name(precommit_data):
    expected_dir_path = PRECOMMIT_LOG_PATH
    expected_file_name: str = f"{precommit_data.block.height}-precommit-data-v{PrecommitDataWriter.VERSION}.json"
    writer = PrecommitDataWriter(os.getcwd())

    # Acts
    writer.write(precommit_data)

    assert os.path.exists(expected_dir_path)
    assert os.path.exists(os.path.join(PRECOMMIT_LOG_PATH, expected_file_name))


def test_precommit_data_check_the_written_json_data(precommit_data, expected_json_data):
    file_name: str = f"{precommit_data.block.height}-precommit-data-v{PrecommitDataWriter.VERSION}.json"
    writer = PrecommitDataWriter(os.getcwd())

    # Acts
    writer.write(precommit_data)

    with open(os.path.join(PRECOMMIT_LOG_PATH, file_name), "r") as f:
        actual_precommit_data = json.load(f)
        for key in expected_json_data.keys():
            assert expected_json_data[key] == actual_precommit_data[key]


def test_precommit_data_when_raising_exception_should_catch_it(precommit_data):
    file_name: str = f"{precommit_data.block.height}-precommit-data-v{PrecommitDataWriter.VERSION}.json"
    precommit_data.rc_block_batch.append("invalid data")

    writer = PrecommitDataWriter(os.getcwd())
    # Set the invalid data to rc block batch (it is going to be a reason of the exception)

    # Act
    writer.write(precommit_data)

    assert os.path.exists(PRECOMMIT_LOG_PATH)
    assert os.path.exists(os.path.join(PRECOMMIT_LOG_PATH, file_name))
