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

import unittest

from iconservice import Address
from iconservice.database.db import ContextDatabase, IconScoreDatabase
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.base.address import AddressPrefix
from iconservice.base.exception import ContainerDBException
from iconservice.iconscore.icon_container_db import ContainerUtil, DictDB, ArrayDB, VarDB
from iconservice.iconscore.icon_score_context import ContextContainer, IconScoreContextFactory
from tests import create_address
from tests.mock_db import MockKeyValueDatabase


class TestIconContainerDB(unittest.TestCase):

    def setUp(self):
        self.db = self.create_db()
        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.DIRECT)

        ContextContainer._push_context(self._context)
        pass

    def tearDown(self):
        ContextContainer._clear_context()
        self.db = None
        pass

    @staticmethod
    def create_db():
        mock_db = MockKeyValueDatabase.create_db()
        context_db = ContextDatabase(mock_db)
        return IconScoreDatabase(create_address(), context_db)

    def test_success_list(self):
        addr1 = create_address(AddressPrefix.CONTRACT)
        test_list = [1, 2, 3, [4, 5, 6], [7, 8, 9, [10, 11, 12]], addr1]
        ContainerUtil.put_to_db(self.db, 'test_list', test_list)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 0, value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 1, value_type=int), 2)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 2, value_type=int), 3)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 3, 0, value_type=int), 4)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 3, 1, value_type=int), 5)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 3, 2, value_type=int), 6)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 0, value_type=int), 7)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 1, value_type=int), 8)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 2, value_type=int), 9)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 3, 0, value_type=int), 10)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 3, 1, value_type=int), 11)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 4, 3, 2, value_type=int), 12)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 5, value_type=Address), addr1)

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

        self.assertEqual(test_dict['a'], 1)

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

        for i in range(range_size, range_size):
            self.assertRaises(ContainerDBException, test_array[i])

        cant_find_value = range_size
        self.assertFalse(cant_find_value in test_array)
        self.assertEqual(range_size, len(test_array))

        for e, i in zip(test_array, range(range_size)):
            self.assertEqual(e, i)

        self.assertEqual(test_array[-1], range(range_size)[-1])

    def test_success_variable(self):
        test_var = VarDB('test_var', self.db, value_type=int)
        self.assertNotEqual(test_var._db, self.db)
        self.assertEqual(test_var._db._prefix, b'\x02')

        test_var.set(10**19+1)

        self.assertEqual(test_var.get(), 10**19+1)

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

    def test_container_util(self):
        prefix: bytes = ContainerUtil.create_db_prefix(ArrayDB, 'a')
        self.assertEqual(b'\x00|a', prefix)

        prefix: bytes = ContainerUtil.create_db_prefix(DictDB, 'dictdb')
        self.assertEqual(b'\x01|dictdb', prefix)

        with self.assertRaises(ContainerDBException):
            prefix: bytes = ContainerUtil.create_db_prefix(VarDB, 'vardb')
