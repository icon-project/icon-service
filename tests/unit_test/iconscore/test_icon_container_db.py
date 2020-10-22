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
from iconservice.iconscore.db import ScoreDatabase
from iconservice.iconscore.icon_container_db import ContainerUtil, DictDB, ArrayDB, VarDB
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from tests import create_address


@pytest.fixture(scope="function")
def score_db(context_db):
    # return IconScoreDatabase(create_address(), context_db)
    return ScoreDatabase(create_address(), context_db)


@pytest.fixture(scope="function", autouse=True)
def context(score_db):
    context = IconScoreContext(IconScoreContextType.DIRECT)
    context.current_address = score_db.address

    ContextContainer._push_context(context)
    yield context
    ContextContainer._clear_context()


class TestIconContainerDB:
    ADDRESS = create_address(AddressPrefix.CONTRACT)

    @pytest.mark.parametrize("args, value_type, expected_value", [
        (0, int, 1),
        (1, int, 2),
        (2, int, 3),
        ((3, 0), int, 4),
        ((3, 1), int, 5),
        ((3, 2), int, 6),
        ((4, 0), int, 7),
        ((4, 1), int, 8),
        ((4, 2), int, 9),
        ((4, 3, 0), int, 10),
        ((4, 3, 1), int, 11),
        ((4, 3, 2), int, 12),
        (5, Address, ADDRESS),
        (6, int, 0)
    ])
    def test_nested_list(self, score_db, args, value_type, expected_value):
        test_list = [1, 2, 3, [4, 5, 6], [7, 8, 9, [10, 11, 12]], self.ADDRESS]
        ContainerUtil.put_to_db(score_db, 'test_list', test_list)

        if isinstance(args, tuple):
            assert ContainerUtil.get_from_db(score_db, 'test_list', *args, value_type=value_type) == expected_value
        else:
            assert ContainerUtil.get_from_db(score_db, 'test_list', args, value_type=value_type) == expected_value

    @pytest.mark.parametrize("args, value_type, expected_value", [
        (1, str, 'a'),
        ((2, 0), str, 'a'),
        ((2, 1), str, 'b'),
        ((2, 2, 0), str, 'c'),
        ((2, 2, 1), str, 'd'),
        ((3, 'a'), int, 1),
        (4, Address, ADDRESS),
    ])
    def test_nested_dict(self, score_db, args, value_type, expected_value):
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}, 4: self.ADDRESS}
        ContainerUtil.put_to_db(score_db, 'test_dict', test_dict)

        if isinstance(args, tuple):
            assert ContainerUtil.get_from_db(score_db, 'test_dict', *args, value_type=value_type) == expected_value
        else:
            assert ContainerUtil.get_from_db(score_db, 'test_dict', args, value_type=value_type) == expected_value

    @pytest.mark.parametrize("args, value_type, expected_value", [
        (0, int, 1),
        (1, int, 2),
        (2, int, 3),
        (3, Address, ADDRESS),
    ])
    def test_tuple(self, score_db, args, value_type, expected_value):
        test_tuple = tuple([1, 2, 3, self.ADDRESS])
        ContainerUtil.put_to_db(score_db, 'test_tuple', test_tuple)

        assert ContainerUtil.get_from_db(score_db, 'test_tuple', args, value_type=value_type) == expected_value

    @staticmethod
    def _check_the_db_prefix_format(name):
        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, name)
        assert prefix == b'\x01|' + name.encode()

    def test_dict_depth1(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, value_type=int)
        self._check_the_db_prefix_format(name)

        test_dict['a'] = 1
        test_dict['b'] = 2

        test_dict['b'] += 1

        assert test_dict['a'] == 1
        assert test_dict['b'] == 3

    def test_dict_other_Key(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, depth=2, value_type=int)
        self._check_the_db_prefix_format(name)

        addr1 = create_address(1)
        addr2 = create_address(0)
        test_dict['a'][addr1] = 1
        test_dict['a'][addr2] = 2

        assert test_dict['a'][addr1] == 1
        assert test_dict['a'][addr2] == 2

    def test_dict_depth2(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, depth=3, value_type=int)
        self._check_the_db_prefix_format(name)

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

    @pytest.mark.parametrize("collection, key_or_index", [
        ({"dummy_key": "dummy_value"}, "not_exists_key"),
        (["dummy_list"], 3)
    ])
    @pytest.mark.parametrize("value_type, expected_value", [
        (int, 0),
        (str, ""),
        (bytes, None),
        (Address, None)
    ])
    def test_default_value_of_container_db(self, score_db, value_type, expected_value, collection, key_or_index):
        # TEST: Check the default value of collection object (dict, list)
        ContainerUtil.put_to_db(score_db, 'test_collection', collection)
        actual_value = ContainerUtil.get_from_db(score_db, 'test_collection', key_or_index, value_type=value_type)

        assert actual_value == expected_value

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
        testarray = ArrayDB(name, score_db, value_type=int)
        assert testarray._db != score_db

        testarray.put(1)
        testarray.put(3)
        testarray.put(5)
        testarray.put(7)
        assert len(testarray) == 4
        assert testarray.pop() == 7
        assert testarray.pop() == 5
        assert len(testarray) == 2

    def test_array_db2(self, score_db):
        name = "TEST"
        testarray = ArrayDB(name, score_db, value_type=int)
        assert testarray._db != score_db

        testarray.put(1)
        testarray.put(2)
        testarray.put(3)
        testarray.put(4)

        assert testarray[0] == 1
        assert testarray[1] == 2
        assert testarray[2] == 3
        assert testarray[3] == 4

        assert testarray[-1] == 4
        assert testarray[-2] == 3
        assert testarray[-3] == 2
        assert testarray[-4] == 1

        testarray[0] = 5
        testarray[1] = 6
        testarray[2] = 7
        testarray[3] = 8

        assert testarray[0] == 5
        assert testarray[1] == 6
        assert testarray[2] == 7
        assert testarray[3] == 8

        testarray[-1] = 4
        testarray[-2] = 3
        testarray[-3] = 2
        testarray[-4] = 1

        assert testarray[-1] == 4
        assert testarray[-2] == 3
        assert testarray[-3] == 2
        assert testarray[-4] == 1

        with pytest.raises(InvalidParamsException):
            testarray[5] = 1
            a = testarray[5]

    @pytest.mark.parametrize("prefix, score_db_cls, expected_prefix", [
        ('a', ArrayDB, b'\x00|a'),
        ('dictdb', DictDB, b'\x01|dictdb'),
    ])
    def test_container_util(self, prefix, score_db_cls, expected_prefix):
        actual_prefix: bytes = ContainerUtil.create_db_prefix(score_db_cls, prefix)
        assert actual_prefix == expected_prefix

    def test_when_create_var_db_prefix_using_container_util_should_raise_error(self):
        with pytest.raises(InvalidParamsException):
            ContainerUtil.create_db_prefix(VarDB, 'vardb')
