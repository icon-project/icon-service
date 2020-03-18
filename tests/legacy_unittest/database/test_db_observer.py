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

from unittest.mock import Mock, patch

import pytest

from iconservice import IconScoreDatabase
from iconservice.base.address import AddressPrefix, Address
from iconservice.database.db import ContextDatabase
from iconservice.database.db import DatabaseObserver
from iconservice.icon_constant import IconScoreContextType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_address


@pytest.fixture(scope="function")
def database_observer():
    return Mock(spec=DatabaseObserver)


@pytest.fixture(scope="function")
def score_db(context_db, database_observer):
    db = IconScoreDatabase(create_address(), context_db)
    db.set_observer(database_observer)
    return db


@pytest.fixture(scope="function")
def context(score_db):
    context = IconScoreContext(IconScoreContextType.DIRECT)
    context.current_address = score_db.address
    ContextContainer._push_context(context)
    yield context
    ContextContainer._clear_context()


def test_database_observer(context, score_db, database_observer):
    # PUT
    key: bytes = b"key1"

    value: bytes = b"value1"

    score_db.put(key, value)
    database_observer.on_put.assert_called()
    args, _ = database_observer.on_put.call_args
    assert key == args[1]
    assert None is args[2]
    assert value == args[3]
    last_value = value

    # UPDATE
    value: bytes = b"value2"

    score_db.put(key, value)
    database_observer.on_put.assert_called()
    args, _ = database_observer.on_put.call_args

    assert key == args[1]
    assert last_value is args[2]
    assert value == args[3]
    last_value = value

    # GET
    key: bytes = b"key1"
    value: bytes = score_db.get(key)
    database_observer.on_get.assert_called()
    args, _ = database_observer.on_get.call_args

    assert key == args[1]
    assert last_value is args[2]
    assert value == last_value

    # DELETE
    key: bytes = b"key1"
    score_db.delete(key)
    database_observer.on_delete.assert_called()
    args, _ = database_observer.on_delete.call_args

    assert key == args[1]
    assert last_value is args[2]
