import unittest
from iconservice.iconscore.icon_container_db import ContainerUtil, DictDB, VarDB
from tests.mock_db import MockDB


class TestIconContainerDB(unittest.TestCase):

    def setUp(self):
        self.db = MockDB(MockDB.make_dict())
        pass

    def tearDown(self):
        self.db = None
        pass

    def test_success_list(self):
        test_list = [1, 2, 3, [4, 5, 6], [7, 8, 9, [10, 11, 12]]]
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

    def test_success_dict(self):
        test_dict = {1: 'a', 2: ['a', 'b', ['c', 'd']], 3: {'a': 1}}
        ContainerUtil.put_to_db(self.db, 'test_dict', test_dict)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 1, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 0, value_type=str), 'a')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 1, value_type=str), 'b')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 0, value_type=str), 'c')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 2, 2, 1, value_type=str), 'd')
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_dict', 3, 'a', value_type=int), 1)

    def test_success_set(self):
        test_set = {1, 2, 3}
        ContainerUtil.put_to_db(self.db, 'test_set', test_set)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_set', 0, value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_set', 1, value_type=int), 2)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_set', 2, value_type=int), 3)

    def test_success_tuple(self):
        test_tuple = tuple([1, 2, 3])
        ContainerUtil.put_to_db(self.db, 'test_tuple', test_tuple)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 0, value_type=int), 1)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 1, value_type=int), 2)
        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_tuple', 2, value_type=int), 3)

    def test_fail_container(self):
        testlist = [[]]
        ContainerUtil.put_to_db(self.db, 'test_list', testlist)

        self.assertEqual(ContainerUtil.get_from_db(self.db, 'test_list', 1, value_type=int), None)

    def test_success_dict_depth1(self):
        test_dict = DictDB('test_dict', self.db, value_type=int)
        test_dict['a'] = 1
        test_dict['b'] = 2

        self.assertEqual(test_dict['a'], 1)

    def test_success_dict_depth2(self):
        test_dict = DictDB('test_dict', self.db, depth=2, value_type=int)
        test_dict['a', 'b'] = 1
        test_dict['a', 'c'] = 2

        self.assertEqual(test_dict['a', 'b'], 1)

    def test_success_variable(self):
        test_var = VarDB('test_var', self.db, value_type=int)
        test_var.set(1)

        self.assertEqual(test_var.get(), 1)
