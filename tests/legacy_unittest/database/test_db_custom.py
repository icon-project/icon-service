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

from unittest.mock import Mock, patch, PropertyMock

import pytest

from iconservice import IconScoreDatabase
from iconservice.base.address import AddressPrefix, Address
from iconservice.database.db import ContextDatabase
from iconservice.database.db import DatabaseObserver
from iconservice.database.score_db.utils import DICT_DB_ID, KeyElement
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.container_db.score_db import ScoreDatabase
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_address


@pytest.fixture(scope="function")
def score_db(context_db):
    patch.object(IconScoreDatabase, '_is_v2', new_callable=PropertyMock)
    db = IconScoreDatabase(create_address(), context_db)
    type(db)._is_v2 = PropertyMock(return_value=False)
    return ScoreDatabase(db=db)


@pytest.fixture(scope="function")
def context(score_db):
    context = IconScoreContext(IconScoreContextType.DIRECT)
    context.current_address = score_db.address
    ContextContainer._push_context(context)
    yield context
    ContextContainer._clear_context()


def test_custom_db_v1(context, score_db):
    # ROOT DB
    key1: bytes = b"key1"
    value1: bytes = b"value1"
    score_db.put(key1, value1)
    ret: bytes = score_db.get(key1)
    assert value1 == ret

    # SUB DB
    prefix1: bytes = b"prefix1"
    key2: bytes = b'key2'
    value2: bytes = b'value2'
    sub_db = score_db.get_sub_db(prefix1)
    sub_db.put(key2, value2)
    ret: bytes = sub_db.get(key2)

    assert value2 == ret


def test_custom_db_v2(context, score_db):
    type(score_db)._is_v2 = PropertyMock(return_value=True)

    # ROOT DB
    key1: bytes = b"key1"
    value1: bytes = b"value1"
    score_db.put(key1, value1)
    ret: bytes = score_db.get(key1)
    assert value1 == ret

    # SUB DB
    prefix1: bytes = b"prefix1"
    key2: bytes = b'key2'
    value2: bytes = b'value2'
    sub_db = score_db.get_sub_db(prefix1)
    sub_db.put(key2, value2)
    ret: bytes = sub_db.get(key2)

    assert value2 == ret


def test_migration(context, score_db):
    # ROOT DB
    key1: bytes = b"key1"
    value1: bytes = b"value1"
    score_db.put(key1, value1)
    ret: bytes = score_db.get(key1)
    assert value1 == ret

    # SUB DB
    prefix1: bytes = b"prefix1"
    key2: bytes = b'key2'
    value2: bytes = b'value2'
    sub_db = score_db.get_sub_db(prefix1)
    sub_db.put(key2, value2)
    ret: bytes = sub_db.get(key2)

    assert value2 == ret

    type(score_db)._is_v2 = PropertyMock(return_value=True)

    ret: bytes = score_db.get(key1)
    assert value1 == ret

    sub_db = score_db.get_sub_db(prefix1)
    ret: bytes = sub_db.get(key2)
    assert value2 == ret
