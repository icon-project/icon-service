# -*- coding: utf-8 -*-
#
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

import pytest

from iconservice import Address
from iconservice.base.address import AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.db import IconScoreDatabase
from iconservice.iconscore.icon_container_db import DictDB, ArrayDB, VarDB
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from tests import create_address


@pytest.fixture(scope="function")
def score_db(context_db):
    return IconScoreDatabase(create_address(), context_db)


@pytest.fixture(scope="function", autouse=True)
def context(score_db):
    context = IconScoreContext(IconScoreContextType.DIRECT)
    context.current_address = score_db.address

    ContextContainer._push_context(context)
    yield context
    ContextContainer._clear_context()


class TestIconContainerDB:
    ADDRESS = create_address(AddressPrefix.CONTRACT)

    def test_dict_depth1(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, value_type=int)

        test_dict['a'] = 1
        test_dict['b'] = 2

        test_dict['b'] += 1

        assert test_dict['a'] == 1
        assert test_dict['b'] == 3

    def test_dict_other_Key(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, depth=2, value_type=int)

        addr1 = create_address(1)
        addr2 = create_address(0)
        test_dict['a'][addr1] = 1
        test_dict['a'][addr2] = 2

        assert test_dict['a'][addr1] == 1
        assert test_dict['a'][addr2] == 2

    def test_dict_depth2(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, depth=3, value_type=int)

        test_dict['a']['b']['c'] = 1
        test_dict['a']['b']['d'] = 2
        test_dict['a']['b']['e'] = 3
        test_dict['a']['b']['f'] = 4

        assert test_dict['a']['b']['c'] == 1

    def test_success_array1(self, score_db):
        test_array = ArrayDB('test_array', score_db, value_type=int)

        range_size = 3

        for i in range(range_size):
            test_array.put(i)

        for i in range(range_size):
            assert test_array[i] == i

        cant_find_value = range_size
        assert (cant_find_value in test_array) is False
        assert len(test_array) == range_size

        for e, i in zip(test_array, range(range_size)):
            assert e == i

        assert test_array[-1] == range(range_size)[-1]

    def test_success_array2(self, score_db):
        test_array = ArrayDB('test_array', score_db, value_type=int)

        range_size = 3
        expect_array = []

        for i in range(range_size):
            expect_array.append(i)
            test_array.put(i)

        for index, e in enumerate(test_array):
            assert e == expect_array[index]

    def test_success_array3(self, score_db):
        test_array = ArrayDB('test_array', score_db, value_type=int)

        range_size = 3
        expect_array = []

        for i in range(range_size):
            expect_array.append(i)
            test_array.put(i)

        if 0 in test_array:
            pass
        else:
            raise Exception()

        if "a" in test_array:
            raise Exception()
        else:
            pass

    def test_success_array4(self, score_db):
        test_array = ArrayDB('test_array', score_db, value_type=int)

        test_array.put(1)
        test_array.put(2)

        with pytest.raises(InvalidParamsException):
            var = test_array[2]
            print(var)

    def test_negative_index_access_in_array_db(self, score_db):
        array = ArrayDB('array', score_db, value_type=int)

        size = 10
        for i in range(size):
            array.put(i)

        negative_index = -1
        for _ in range(size):
            index = size + negative_index
            assert array[index] == array[negative_index]
            negative_index -= 1

    @pytest.mark.parametrize("value_type, expected_value", [
        (int, 10 ** 19 + 1),
        (Address, create_address(AddressPrefix.CONTRACT)),
        (Address, create_address(AddressPrefix.EOA))
    ])
    def test_var_db(self, score_db, value_type, expected_value):
        test_var = VarDB('test_var', score_db, value_type=value_type)
        assert test_var._db != score_db

        test_var.set(expected_value)

        assert test_var.get() == expected_value

    @pytest.mark.parametrize("value_type, expected_value", [
        (int, 0),
        (str, ""),
        (bytes, None),
        (Address, None)
    ])
    def test_default_value_of_var_db(self, score_db, value_type, expected_value):
        # var_db
        test_var = VarDB('test_var', score_db, value_type=value_type)
        assert test_var.get() == expected_value

    def test_array_db(self, score_db):
        name = "TEST"
        test_array = ArrayDB(name, score_db, value_type=int)
        assert test_array._db != score_db

        test_array.put(1)
        test_array.put(3)
        test_array.put(5)
        test_array.put(7)
        assert len(test_array) == 4
        assert test_array.pop() == 7
        assert test_array.pop() == 5
        assert len(test_array) == 2

    def test_array_db2(self, score_db):
        name = "TEST"
        test_array = ArrayDB(name, score_db, value_type=int)
        assert test_array._db != score_db

        test_array.put(1)
        test_array.put(2)
        test_array.put(3)
        test_array.put(4)

        assert test_array[0] == 1
        assert test_array[1] == 2
        assert test_array[2] == 3
        assert test_array[3] == 4

        assert test_array[-1] == 4
        assert test_array[-2] == 3
        assert test_array[-3] == 2
        assert test_array[-4] == 1

        test_array[0] = 5
        test_array[1] = 6
        test_array[2] = 7
        test_array[3] = 8

        assert test_array[0] == 5
        assert test_array[1] == 6
        assert test_array[2] == 7
        assert test_array[3] == 8

        test_array[-1] = 4
        test_array[-2] = 3
        test_array[-3] = 2
        test_array[-4] = 1

        assert test_array[-1] == 4
        assert test_array[-2] == 3
        assert test_array[-3] == 2
        assert test_array[-4] == 1

        with pytest.raises(InvalidParamsException):
            test_array[5] = 1
            a = test_array[5]
