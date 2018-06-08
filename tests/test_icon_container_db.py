import unittest

from iconservice import Address
from iconservice.base.address import create_address, AddressPrefix
from iconservice.base.exception import ContainerDBException
from iconservice.iconscore.icon_container_db import ContainerUtil, DictDB, ArrayDB, VarDB
from tests.mock_db import create_mock_icon_score_db


class TestIconContainerDB(unittest.TestCase):

    def setUp(self):
        self.db = create_mock_icon_score_db()
        pass

    def tearDown(self):
        self.db = None
        pass

    def test_success_list(self):
        test_list = [1, 2, 3, [4, 5, 6], [7, 8, 9, [10, 11, 12]], create_address(AddressPrefix.EOA, b'123')]
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
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 5, value_type=Address),
                         create_address(AddressPrefix.EOA, b'123'))

    def test_success_dict(self):
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}, 4: create_address(AddressPrefix.CONTRACT, b'123')}
        ContainerUtil.put_to_db(self.db, 'test_dict', test_dict)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 1, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 0, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 1, value_type=str), 'b')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 0, value_type=str), 'c')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 1, value_type=str), 'd')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'a', value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 4, value_type=Address),
                         create_address(AddressPrefix.CONTRACT, b'123'))

    def test_success_tuple(self):
        test_tuple = tuple([1, 2, 3, create_address(AddressPrefix.CONTRACT, b'234')])
        ContainerUtil.put_to_db(self.db, 'test_tuple', test_tuple)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 0, value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 1, value_type=int), 2)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 2, value_type=int), 3)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 3, value_type=Address),
                         create_address(AddressPrefix.CONTRACT, b'234'))

    def test_fail_container(self):
        testlist = [[]]
        ContainerUtil.put_to_db(self.db, 'test_list', testlist)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 1, value_type=int), 0)

    def test_success_dict_depth1(self):
        test_dict = DictDB('test_dict', self.db, value_type=int)
        test_dict['a'] = 1
        test_dict['b'] = 2

        self.assertEqual(test_dict['a'], 1)

    def test_success_dict_depth2(self):
        test_dict = DictDB('test_dict', self.db, depth=3, value_type=int)
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
        test_var.set(10**19+1)

        self.assertEqual(test_var.get(), 10**19+1)

        test_var2 = VarDB(2,
                          self.db, value_type=Address)
        address = create_address(AddressPrefix.CONTRACT, b'test_var2')
        test_var2.set(address)
        data = test_var2.get()
        self.assertEqual(data, address)

        test_var4 = VarDB(4,
                          self.db, value_type=Address)

        address3 = create_address(AddressPrefix.from_string('cx'), b'test_var4')
        test_var4.set(address3)
        self.assertEqual(test_var4.get(), address3)

    def test_default_val_db(self):
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}}
        ContainerUtil.put_to_db(self.db, 'test_dict', test_dict)

        # dict_db
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'b', value_type=int), 0)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=str), "")
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=bytes), b"")
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'c', value_type=Address), None)

        # list_db
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=str), '')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=int), 0)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=bytes), b'')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 3, value_type=Address), None)

        # var_db
        test_var = VarDB('test_var', self.db, value_type=int)
        self.assertEqual(test_var.get(), 0)
        test_var2 = VarDB('test_var2', self.db, value_type=str)
        self.assertEqual(test_var2.get(), "")
        test_var3 = VarDB('test_var3', self.db, value_type=bytes)
        self.assertEqual(test_var3.get(), b'')
        test_var4 = VarDB('test_var4', self.db, value_type=Address)
        self.assertEqual(test_var4.get(), None)
