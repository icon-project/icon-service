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
from iconservice.database.db import IconScoreDatabase
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_container_db import ContainerUtil, DictDB, ArrayDB, VarDB
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
    ])
    def test_success_list(self, score_db, args, value_type, expected_value):
        test_list = [1, 2, 3, [4, 5, 6], [7, 8, 9, [10, 11, 12]], self.ADDRESS]
        ContainerUtil.put_to_db(score_db, 'test_list', test_list)

        if isinstance(args, tuple):
            assert ContainerUtil.get_from_db(score_db, 'test_list', *args, value_type=value_type) == expected_value
        else:
            assert ContainerUtil.get_from_db(score_db, 'test_list', args, value_type=value_type) == expected_value

    def test_success_dict(self):
        addr1 = create_address(AddressPrefix.CONTRACT)
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}, 4: addr1}
        ContainerUtil.put_to_db(self.db, 'test_dict', test_dict)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 1, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 0, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 1, value_type=str), 'b')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 0, value_type=str), 'c')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 1, value_type=str), 'd')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'a', value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 4, value_type=Address), addr1)

    def test_success_tuple(self):
        addr1 = create_address(AddressPrefix.CONTRACT)
        test_tuple = tuple([1, 2, 3, addr1])
        ContainerUtil.put_to_db(self.db, 'test_tuple', test_tuple)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 0, value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 1, value_type=int), 2)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 2, value_type=int), 3)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 3, value_type=Address), addr1)

    def test_fail_container(self):
        testlist = [[]]
        ContainerUtil.put_to_db(self.db, 'test_list', testlist)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 1, value_type=int), 0)

    def test_success_dict_depth1(self):
        name = 'test_dict'
        test_dict = DictDB(name, self.db, value_type=int)

        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, name)
        self.assertEqual(b'\x01|' + name.encode(), prefix)

        test_dict['a'] = 1
        test_dict['b'] = 2

        test_dict['b'] += 1

        self.assertEqual(test_dict['a'], 1)
        self.assertEqual(test_dict['b'], 3)

    def test_success_dict_other_Key(self):
        name = 'test_dict'
        test_dict = DictDB(name, self.db, depth=2, value_type=int)

        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, name)
        self.assertEqual(b'\x01|' + name.encode(), prefix)

        addr1 = create_address(1)
        addr2 = create_address(0)
        test_dict['a'][addr1] = 1
        test_dict['a'][addr2] = 2

        self.assertEqual(test_dict['a'][addr1], 1)
        self.assertEqual(test_dict['a'][addr2], 2)

    def test_success_dict_depth2(self):
        name = 'test_dict'
        test_dict = DictDB(name, self.db, depth=3, value_type=int)

        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, name)
        self.assertEqual(b'\x01|' + name.encode(), prefix)

        test_dict['a']['b']['c'] = 1
        test_dict['a']['b']['d'] = 2
        test_dict['a']['b']['e'] = 3
        test_dict['a']['b']['f'] = 4

        self.assertEqual(test_dict['a']['b']['c'], 1)

    def test_success_array1(self):
        test_array = ArrayDB('test_array', self.db, value_type=int)

        range_size = 3

        for i in range(range_size):
            test_array.put(i)

        for i in range(range_size):
            self.assertEqual(test_array[i], i)

        cant_find_value = range_size
        self.assertFalse(cant_find_value in test_array)
        self.assertEqual(range_size, len(test_array))

        for e, i in zip(test_array, range(range_size)):
            self.assertEqual(e, i)

        self.assertEqual(test_array[-1], range(range_size)[-1])

    def test_success_array2(self):
        test_array = ArrayDB('test_array', self.db, value_type=int)

        range_size = 3
        expect_array = []

        for i in range(range_size):
            expect_array.append(i)
            test_array.put(i)

        for index, e in enumerate(test_array):
            self.assertEqual(e, expect_array[index])

    def test_success_array3(self):
        test_array = ArrayDB('test_array', self.db, value_type=int)

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

    def test_success_array4(self):
        test_array = ArrayDB('test_array', self.db, value_type=int)

        test_array.put(1)
        test_array.put(2)

        with self.assertRaises(InvalidParamsException):
            var = test_array[2]
            print(var)

    def test_negative_index_access_in_array_db(self):
        array = ArrayDB('array', self.db, value_type=int)

        size = 10
        for i in range(size):
            array.put(i)

        negative_index = -1
        for _ in range(size):
            index = size + negative_index
            self.assertEqual(array[index], array[negative_index])
            negative_index -= 1

    def test_success_variable(self):
        test_var = VarDB('test_var', self.db, value_type=int)
        self.assertNotEqual(test_var._db, self.db)
        self.assertEqual(test_var._db._prefix, b'\x02')

        test_var.set(10 ** 19 + 1)

        self.assertEqual(test_var.get(), 10 ** 19 + 1)

        test_var2 = VarDB(2,
                          self.db, value_type=Address)
        address = create_address(AddressPrefix.CONTRACT)
        test_var2.set(address)
        data = test_var2.get()
        self.assertEqual(data, address)

        test_var4 = VarDB(4,
                          self.db, value_type=Address)

        address3 = create_address(AddressPrefix.CONTRACT)
        test_var4.set(address3)
        self.assertEqual(test_var4.get(), address3)

    def test_default_val_db(self):
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}}
        ContainerUtil.put_to_db(self.db, 'test_dict', test_dict)

        # dict_db
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'b', value_type=int), 0)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=str), "")
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=bytes), None)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=Address), None)

        # list_db
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=str), '')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=int), 0)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=bytes), None)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=Address), None)

        # var_db
        test_var = VarDB('test_var', self.db, value_type=int)
        self.assertEqual(test_var.get(), 0)
        test_var2 = VarDB('test_var2', self.db, value_type=str)
        self.assertEqual(test_var2.get(), "")
        test_var3 = VarDB('test_var3', self.db, value_type=bytes)
        self.assertEqual(test_var3.get(), None)
        test_var4 = VarDB('test_var4', self.db, value_type=Address)
        self.assertEqual(test_var4.get(), None)

    def test_array_db(self):
        name = "TEST"
        testarray = ArrayDB(name, self.db, value_type=int)
        self.assertNotEqual(testarray._db, self.db)
        self.assertEqual(
            testarray._db._prefix,
            ContainerUtil.create_db_prefix(ArrayDB, name))

        testarray.put(1)
        testarray.put(3)
        testarray.put(5)
        testarray.put(7)
        self.assertEqual(4, len(testarray))
        self.assertEqual(7, testarray.pop())
        self.assertEqual(5, testarray.pop())
        self.assertEqual(2, len(testarray))

    def test_array_db2(self):
        name = "TEST"
        testarray = ArrayDB(name, self.db, value_type=int)
        self.assertNotEqual(testarray._db, self.db)
        self.assertEqual(
            testarray._db._prefix,
            ContainerUtil.create_db_prefix(ArrayDB, name))

        testarray.put(1)
        testarray.put(2)
        testarray.put(3)
        testarray.put(4)

        self.assertEqual(1, testarray[0])
        self.assertEqual(2, testarray[1])
        self.assertEqual(3, testarray[2])
        self.assertEqual(4, testarray[3])

        self.assertEqual(4, testarray[-1])
        self.assertEqual(3, testarray[-2])
        self.assertEqual(2, testarray[-3])
        self.assertEqual(1, testarray[-4])

        testarray[0] = 5
        testarray[1] = 6
        testarray[2] = 7
        testarray[3] = 8

        self.assertEqual(5, testarray[0])
        self.assertEqual(6, testarray[1])
        self.assertEqual(7, testarray[2])
        self.assertEqual(8, testarray[3])

        testarray[-1] = 4
        testarray[-2] = 3
        testarray[-3] = 2
        testarray[-4] = 1

        self.assertEqual(4, testarray[-1])
        self.assertEqual(3, testarray[-2])
        self.assertEqual(2, testarray[-3])
        self.assertEqual(1, testarray[-4])

        with self.assertRaises(InvalidParamsException):
            testarray[5] = 1
            a = testarray[5]

    def test_container_util(self):
        prefix: bytes = ContainerUtil.create_db_prefix(ArrayDB, 'a')
        self.assertEqual(b'\x00|a', prefix)

        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, 'dictdb')
        self.assertEqual(b'\x01|dictdb', prefix)

        with self.assertRaises(InvalidParamsException):
            prefix: bytes = ContainerUtil.create_db_prefix(VarDB, 'vardb')
