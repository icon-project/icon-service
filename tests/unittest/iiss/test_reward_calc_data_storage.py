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

import os
from unittest.mock import Mock

import pytest

from iconservice.database.db import KeyValueDatabase
from iconservice.database.wal import IissWAL
from iconservice.icon_constant import Revision, RC_DB_VERSION_0, RC_DB_VERSION_2
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.data_creator import *
from iconservice.iiss.reward_calc.msg_data import TxType
from iconservice.iiss.reward_calc.storage import get_rc_version
from iconservice.utils import sha3_256
from iconservice.utils.msgpack_for_db import MsgPackForDB
from tests import create_address
from tests.legacy_unittest.iiss.mock_rc_db import MockIissDataBase
from tests.legacy_unittest.mock_db import MockPlyvelDB

DUMMY_BLOCK_HEIGHT = 1
CONFIG_MAIN_PREP_COUNT = 28
CONFIG_SUB_PREP_COUNT = 78


@pytest.fixture()
def dummy_header():
    dummy_block_height = DUMMY_BLOCK_HEIGHT
    header = Header()
    header.block_height = dummy_block_height
    header.version = RC_DB_VERSION_0
    return header


@pytest.fixture()
def dummy_gv():
    gv = GovernanceVariable()
    gv.block_height = DUMMY_BLOCK_HEIGHT
    gv.config_main_prep_count = CONFIG_MAIN_PREP_COUNT
    gv.config_sub_prep_count = CONFIG_SUB_PREP_COUNT
    gv.calculated_irep = 1
    gv.reward_rep = 1000
    return gv


@pytest.fixture()
def dummy_prep():
    prep = PRepsData()
    prep.block_height = DUMMY_BLOCK_HEIGHT
    prep.total_delegation = 10
    prep.prep_list = []
    return prep


@pytest.fixture()
def dummy_tx():
    tx = TxData()
    tx.address = create_address()
    tx.block_height = DUMMY_BLOCK_HEIGHT
    tx.type = TxType.PREP_REGISTER
    tx.data = PRepRegisterTx()
    return tx


@pytest.fixture
def context():
    context = Mock(spec=IconScoreContext)
    return context


@pytest.fixture
def rc_data_storage(context, mocker):
    mocker.patch.object(KeyValueDatabase, "from_path")
    mocker.patch.object(RewardCalcStorage, "_supplement_db")
    context.revision = Revision.DECENTRALIZATION.value

    KeyValueDatabase.from_path.side_effect = MockIissDataBase.from_path
    path = ""
    rc_data_storage = RewardCalcStorage()
    rc_data_storage.open(context, path)

    return rc_data_storage


@pytest.fixture(scope="function", autouse=True)
def mock_os_path_exists(mocker):
    mocker.patch.object(os.path, "exists")


def expected_rc_data_by_revision(revision: int):
    if revision < Revision.DECENTRALIZATION.value:
        expected_header_revision = 0
        expected_gv_config_main_prep_count = 0
        expected_gv_config_sub_prep_count = 0
        return (
            RC_DB_VERSION_0,
            expected_header_revision,
            expected_gv_config_main_prep_count,
            expected_gv_config_sub_prep_count,
        )
    else:
        expected_header_revision = revision
        expected_gv_config_main_prep_count = CONFIG_MAIN_PREP_COUNT
        expected_gv_config_sub_prep_count = CONFIG_SUB_PREP_COUNT
        return (
            RC_DB_VERSION_2,
            expected_header_revision,
            expected_gv_config_main_prep_count,
            expected_gv_config_sub_prep_count,
        )


class TestRcDataStorage:
    @pytest.mark.parametrize(
        "revision, "
        "expected_rc_db_version, "
        "expected_header_revision, "
        "expected_gv_config_main_prep_count, "
        "expected_gv_config_sub_prep_count",
        [(rev.value, *expected_rc_data_by_revision(rev.value)) for rev in Revision],
    )
    def test_rc_storage_check_data_format_by_revision(
        self,
        context,
        rc_data_storage,
        dummy_header,
        dummy_gv,
        revision,
        expected_rc_db_version,
        expected_header_revision,
        expected_gv_config_main_prep_count,
        expected_gv_config_sub_prep_count,
    ):
        # TEST: After DECENTRALIZE revision, verion should be 2 (before 0)
        context.revision = revision

        current_version = get_rc_version(revision)

        assert current_version == expected_rc_db_version

        # Setup to test below
        dummy_header.version = current_version
        dummy_header.revision = revision
        dummy_gv.version = current_version
        iiss_data = [dummy_header, dummy_gv]
        iiss_wal: "IissWAL" = IissWAL(iiss_data, -1, revision)
        rc_data_storage.commit(iiss_wal)

        # TEST: Header's values should be below
        # RC version 0: version should be 0 and revision should be 0
        # RC version 2: version should be 2 and revision should be current revision
        header: bytes = rc_data_storage._db.get(dummy_header.make_key())
        header: "Header" = Header.from_bytes(header)
        assert header.version == expected_rc_db_version
        assert header.revision == expected_header_revision

        # TEST: GV's values should be below
        # RC version 0: version should be 0 and main, sub prep count should be 0
        # RC version 2: version should be 2 and main, sub prep count should be each 28, 78
        gv_key: bytes = dummy_gv.make_key()
        gv: bytes = rc_data_storage._db.get(dummy_gv.make_key())
        gv: "GovernanceVariable" = GovernanceVariable.from_bytes(gv_key, gv)
        assert gv.version == expected_rc_db_version
        assert gv.config_main_prep_count == expected_gv_config_main_prep_count
        assert gv.config_sub_prep_count == expected_gv_config_sub_prep_count

    def test_open(self, context, mock_os_path_exists, mocker):
        # TEST: When input path, make path of current_db and iiss_rc_db and generate current level db(if not exist)
        context.revision = Revision.DECENTRALIZATION.value
        mocker.patch.object(KeyValueDatabase, "from_path")
        mocker.patch.object(RewardCalcStorage, "_supplement_db")
        rc_data_storage = RewardCalcStorage()
        test_db_path: str = os.path.join(os.getcwd(), ".storage_test_db")

        def from_path(path: str, create_if_missing: bool = True) -> "MockIissDataBase":
            expected_current_db_path = os.path.join(
                test_db_path, RewardCalcStorage.CURRENT_IISS_DB_NAME
            )
            assert path == expected_current_db_path
            assert create_if_missing is True
            db = MockPlyvelDB(MockPlyvelDB.make_db())
            return MockIissDataBase(db)

        KeyValueDatabase.from_path.side_effect = from_path

        # Act
        rc_data_storage.open(context, test_db_path)

        os.path.exists.assert_called()
        assert rc_data_storage._db_iiss_tx_index == -1

    def test_when_initially_load_last_tx_index_should_return_minus_1(
        self, rc_data_storage
    ):
        actual_index = rc_data_storage._load_last_transaction_index()

        assert actual_index == -1

    def test_load_last_tx_index(self, rc_data_storage):
        current_db = rc_data_storage._db

        for expected_index in range(0, 200):
            dummy_last_tx_index_info = expected_index.to_bytes(8, "big")
            current_db.put(b"last_transaction_index", dummy_last_tx_index_info)

            assert rc_data_storage._load_last_transaction_index() == expected_index

    @pytest.mark.parametrize(
        "block_height", [block_height for block_height in range(-2, 1)]
    )
    def test_replace_db_invalid_block_height(self, rc_data_storage, block_height):
        with pytest.raises(AssertionError):
            rc_data_storage.replace_db(block_height)

    def test_commit_without_iiss_tx(
        self, dummy_header, dummy_gv, dummy_prep, rc_data_storage
    ):
        # TEST: when there is no iiss_tx data, index should not be increased
        dummy_iiss_data_list_without_iiss_tx = [dummy_header, dummy_gv, dummy_prep]
        iiss_wal: "IissWAL" = IissWAL(
            dummy_iiss_data_list_without_iiss_tx, -1, Revision.IISS.value
        )

        rc_data_storage.commit(iiss_wal)

        assert rc_data_storage._db_iiss_tx_index == -1
        assert (
            rc_data_storage._db.get(
                rc_data_storage.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX
            )
            is None
        )

    def test_commit_with_iiss_tx(
        self, dummy_header, dummy_gv, dummy_prep, dummy_tx, rc_data_storage
    ):
        # TEST: When commit with iiss_tx data, tx index should be increased
        # and cached index and db stored index should be equal
        actual_recorded_index: int = -1
        for expected_index in range(0, 10):
            dummy_iiss_data_list = [dummy_header, dummy_gv, dummy_prep, dummy_tx]
            iiss_wal: "IissWAL" = IissWAL(
                dummy_iiss_data_list,
                rc_data_storage._db_iiss_tx_index,
                Revision.IISS.value,
            )

            rc_data_storage.commit(iiss_wal)

            actual_recorded_index = int.from_bytes(
                rc_data_storage._db.get(
                    rc_data_storage.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX
                ),
                "big",
            )
            assert (
                rc_data_storage._db_iiss_tx_index
                == actual_recorded_index
                == expected_index
            )

        # Check the each tx data's prefix
        expected_tx_index: int = 0
        actual_tx_index: int = -1
        for key in rc_data_storage._db.iterator():
            if key[:2] == b"TX":
                actual_tx_index = int.from_bytes(key[2:], "big")
                assert actual_tx_index == expected_tx_index
                expected_tx_index += 1

        # Last tx data's index prefix and tx index should be equal
        assert actual_tx_index == actual_recorded_index

    def test_get_calc_response_before_put_it(self, rc_data_storage):
        # TEST: If there is no prev_calc_period_issued_i_score, should return None
        actual_i_score, _, _ = rc_data_storage.get_calc_response_from_rc()

        assert actual_i_score == -1

    def test_putting_i_score_data_on_current_db_and_get_from_the_db(
        self, rc_data_storage
    ):
        # TEST: Put i-score response and get it from the db
        expected_i_score = 10_000
        expected_version = 1
        expected_block_height = 0
        expected_state_hash: bytes = sha3_256(b"state_hash")

        rc_data_storage.put_calc_response_from_rc(
            expected_i_score, expected_block_height, expected_state_hash
        )
        actual_i_score_db_data = MsgPackForDB.loads(
            rc_data_storage._db.get(rc_data_storage.KEY_FOR_CALC_RESPONSE_FROM_RC)
        )

        assert actual_i_score_db_data[0] == expected_version
        assert actual_i_score_db_data[1] == expected_i_score
        assert actual_i_score_db_data[2] == expected_block_height
        assert actual_i_score_db_data[3] == expected_state_hash

        # TEST: Put i-score response and get using get_calc_response_from_rc method
        actual_i_score, _, _ = rc_data_storage.get_calc_response_from_rc()

        assert actual_i_score == expected_i_score
