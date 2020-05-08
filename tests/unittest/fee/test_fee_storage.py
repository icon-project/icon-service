#!/usr/bin/env python
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

from shutil import rmtree
from unittest import main

import pytest

from iconservice.base.address import AddressPrefix
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.database.db import ContextDatabase
from iconservice.fee import FeeStorage
from iconservice.fee.deposit import Deposit
from iconservice.fee.deposit_meta import DepositMeta
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from tests import create_address, create_tx_hash


@pytest.fixture(scope="function")
def context():
    context = IconScoreContext(IconScoreContextType.DIRECT)
    context.tx_batch = TransactionBatch()
    context.block_batch = BlockBatch()
    yield context


@pytest.fixture(scope="function")
def storage():
    db_name = 'fee.db'
    db = ContextDatabase.from_path(db_name)
    assert db is not None
    storage = FeeStorage(db)
    yield storage
    db.key_value_db.close()
    rmtree(db_name)


def test_get_put_delete_score_fee(context, storage):
    score_address = create_address(AddressPrefix.CONTRACT)

    deposit_meta = DepositMeta()
    deposit_meta.head_id = create_tx_hash()
    deposit_meta.tail_id = create_tx_hash()
    deposit_meta.available_head_id_of_deposit = create_tx_hash()
    deposit_meta.available_head_id_of_virtual_step = create_tx_hash()
    storage.put_deposit_meta(context, score_address, deposit_meta)

    deposit_meta_2 = storage.get_deposit_meta(context, score_address)
    assert deposit_meta == deposit_meta_2

    storage.delete_deposit_meta(context, score_address)
    deposit_meta_2 = storage.get_deposit_meta(context, score_address)
    assert deposit_meta_2 is None


def test_get_put_delete_score_fee_with_none_type(context, storage):
    score_address = create_address(AddressPrefix.CONTRACT)

    deposit_meta = DepositMeta()
    storage.put_deposit_meta(context, score_address, deposit_meta)

    deposit_meta_2 = storage.get_deposit_meta(context, score_address)
    assert deposit_meta == deposit_meta_2

    storage.delete_deposit_meta(context, score_address)
    deposit_meta_2 = storage.get_deposit_meta(context, score_address)
    assert deposit_meta_2 is None


def test_get_put_delete_deposit(context, storage):
    context = context

    deposit = Deposit()
    deposit.id = create_tx_hash()
    deposit.score_address = create_address(AddressPrefix.CONTRACT)
    deposit.sender = create_address(AddressPrefix.EOA)
    deposit.deposit_amount = 10000
    deposit.deposit_used = 10000
    deposit.created = 10
    deposit.expires = 1000000
    deposit.virtual_step_issued = 100000000000
    deposit.virtual_step_used = 200000000000
    deposit.prev_id = create_tx_hash()
    deposit.next_id = create_tx_hash()
    deposit.version = 2
    storage.put_deposit(context, deposit)

    deposit2 = storage.get_deposit(context, deposit.id)
    assert deposit == deposit2
    assert deposit.id == deposit2.id

    storage.delete_deposit(context, deposit.id)
    deposit2 = storage.get_deposit(context, deposit.id)
    assert deposit2 is None

def test_get_put_delete_deposit_with_none_type(context, storage):
    context = context

    deposit = Deposit()
    deposit.id = create_tx_hash()
    deposit.score_address = create_address(AddressPrefix.CONTRACT)
    deposit.sender = create_address(AddressPrefix.EOA)
    deposit.deposit_amount = 10000
    deposit.deposit_used = 10000
    deposit.created = 10
    deposit.expires = 1000000
    deposit.virtual_step_issued = 100000000000
    deposit.virtual_step_used = 200000000000
    deposit.version = 1
    storage.put_deposit(context, deposit)

    deposit2 = storage.get_deposit(context, deposit.id)
    assert deposit == deposit2
    assert deposit.id == deposit2.id

    storage.delete_deposit(context, deposit.id)
    deposit2 = storage.get_deposit(context, deposit.id)
    assert deposit2 is None
