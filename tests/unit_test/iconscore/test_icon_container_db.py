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
from unittest import mock
from unittest.mock import PropertyMock, patch

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.database.db import ScoreDatabase
from iconservice.iconscore.container_db.score_db import IconScoreDatabase
from iconservice.database.score_db.utils import DICT_DB_ID, KeyElement, ARRAY_DB_ID, VAR_DB_ID
from iconservice.iconscore.container_db.utils import Utils as ContainerUtils
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_container_db import DictDB, ArrayDB, VarDB
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from iconservice.utils import int_to_bytes
from tests import create_address


@pytest.fixture(scope="function")
def score_db(context_db):
    patch.object(IconScoreDatabase, '_is_v2', new_callable=PropertyMock)
    db = ScoreDatabase(create_address(), context_db)
    type(db)._is_v2 = PropertyMock(return_value=False)
    return IconScoreDatabase(db=db.get_sub_db())


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
        ContainerUtils.put_to_db(score_db, 'test_list', test_list)

        if isinstance(args, tuple):
            assert ContainerUtils.get_from_db(score_db, 'test_list', *args, value_type=value_type) == expected_value
        else:
            assert ContainerUtils.get_from_db(score_db, 'test_list', args, value_type=value_type) == expected_value

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
        ContainerUtils.put_to_db(score_db, 'test_dict', test_dict)

        if isinstance(args, tuple):
            assert ContainerUtils.get_from_db(score_db, 'test_dict', *args, value_type=value_type) == expected_value
        else:
            assert ContainerUtils.get_from_db(score_db, 'test_dict', args, value_type=value_type) == expected_value

    @pytest.mark.parametrize("args, value_type, expected_value", [
        (0, int, 1),
        (1, int, 2),
        (2, int, 3),
        (3, Address, ADDRESS),
    ])
    def test_tuple(self, score_db, args, value_type, expected_value):
        test_tuple = tuple([1, 2, 3, self.ADDRESS])
        ContainerUtils.put_to_db(score_db, 'test_tuple', test_tuple)

        assert ContainerUtils.get_from_db(score_db, 'test_tuple', args, value_type=value_type) == expected_value

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

    def test_dict_depth_seperate(self, score_db):
        name = 'test_dict'
        test_dict = DictDB(name, score_db, value_type=bytes)
        test_dict[b'a|b'] = b'a'

        test_dict = DictDB(name, score_db, value_type=bytes)
        v = test_dict[b'a|b']
        print("result", v)

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
        assert test_var._db._score_db._prefix == score_db.address.to_bytes()

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
        ContainerUtils.put_to_db(score_db, 'test_collection', collection)
        actual_value = ContainerUtils.get_from_db(score_db, 'test_collection', key_or_index, value_type=value_type)
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

    @pytest.mark.parametrize(
        "is_v2,expected",
        [
            (False, b'|'.join((
                    b'sub1',
                    b'sub2',
                    b'sub3',
                    b'sub4',
                    DICT_DB_ID,
                    b'test_dict',
                    DICT_DB_ID,
                    b'aaaa',
                    DICT_DB_ID,
                    b'bbbb',
                    DICT_DB_ID,
                    b'cccc',
                    b'dddd'
            ))),
            (True, b''.join((
                    DICT_DB_ID,
                    KeyElement._rlp_encode_bytes(b'test_dict'),
                    KeyElement._rlp_encode_bytes(b'sub1'),
                    KeyElement._rlp_encode_bytes(b'sub2'),
                    KeyElement._rlp_encode_bytes(b'sub3'),
                    KeyElement._rlp_encode_bytes(b'sub4'),
                    KeyElement._rlp_encode_bytes(b'aaaa'),
                    KeyElement._rlp_encode_bytes(b'bbbb'),
                    KeyElement._rlp_encode_bytes(b'cccc'),
                    KeyElement._rlp_encode_bytes(b'dddd')
            ))),
        ]
    )
    def test_dict_db_check_prefix(self, score_db, is_v2, expected):
        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=is_v2)

        if is_v2:
            sep: bytes = b''
        else:
            sep: bytes = b'|'
        expected: bytes = sep.join((score_db.address.to_bytes(), expected))

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test_dict'
        key1 = b'aaaa'
        key2 = b'bbbb'
        key3 = b'cccc'
        key4 = b'dddd'
        depth = 4
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_dict = DictDB(name, sub_db, value_type=bytes, depth=depth)

        def _get_context_db(score_db):
            return score_db._db._score_db._context_db

        _get_context_db(score_db).put = mock.Mock()
        _get_context_db(score_db).get = mock.Mock(return_value=value)
        _get_context_db(score_db).delete = mock.Mock()

        test_dict[key1][key2][key3][key4] = value

        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected
        ret = test_dict[key1][key2][key3][key4]
        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected
        del test_dict[key1][key2][key3][key4]
        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected

    @pytest.mark.parametrize(
        "is_v2,expected1,expected2",
        [
            (
                    False,
                    b'|'.join(
                        (
                                b'sub1',
                                b'sub2',
                                b'sub3',
                                b'sub4',
                                ARRAY_DB_ID,
                                b'test_array',
                                int_to_bytes(0)
                        )
                    ),
                    b'|'.join(
                        (
                                b'sub1',
                                b'sub2',
                                b'sub3',
                                b'sub4',
                                ARRAY_DB_ID,
                                b'test_array',
                                b'size'
                        )
                    )
            ),
            (
                    True,
                    b''.join(
                        (
                                ARRAY_DB_ID,
                                KeyElement._rlp_encode_bytes(b'test_array'),
                                KeyElement._rlp_encode_bytes(b'sub1'),
                                KeyElement._rlp_encode_bytes(b'sub2'),
                                KeyElement._rlp_encode_bytes(b'sub3'),
                                KeyElement._rlp_encode_bytes(b'sub4'),
                                KeyElement._rlp_encode_bytes(int_to_bytes(0))
                        )
                    ),
                    b''.join(
                        (
                                ARRAY_DB_ID,
                                KeyElement._rlp_encode_bytes(b'test_array'),
                                KeyElement._rlp_encode_bytes(b'sub1'),
                                KeyElement._rlp_encode_bytes(b'sub2'),
                                KeyElement._rlp_encode_bytes(b'sub3'),
                                KeyElement._rlp_encode_bytes(b'sub4'),
                                KeyElement._rlp_encode_bytes(b'')
                        )
                    )
            )
        ]
    )
    def test_array_db_check_prefix(self, score_db, is_v2, expected1, expected2):
        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=is_v2)

        if is_v2:
            sep: bytes = b''
        else:
            sep: bytes = b'|'
        expected1: bytes = sep.join((score_db.address.to_bytes(), expected1))
        expected2: bytes = sep.join((score_db.address.to_bytes(), expected2))

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test_array'
        depth = 1
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_array = ArrayDB(name, sub_db, value_type=bytes, depth=depth)

        def _get_context_db(score_db):
            return score_db._db._score_db._context_db

        _get_context_db(score_db).put = mock.Mock()

        test_array.put(value)

        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected1

        args, _ = _get_context_db(score_db).put.call_args_list[1]
        assert args[1] == expected2


    @pytest.mark.parametrize(
        "is_v2,expected",
        [
            (False, b'|'.join((
                    b'sub1',
                    b'sub2',
                    b'sub3',
                    b'sub4',
                    VAR_DB_ID,
                    b'test_var',
            ))),
            (True, b''.join((
                    VAR_DB_ID,
                    KeyElement._rlp_encode_bytes(b'test_var'),
                    KeyElement._rlp_encode_bytes(b'sub1'),
                    KeyElement._rlp_encode_bytes(b'sub2'),
                    KeyElement._rlp_encode_bytes(b'sub3'),
                    KeyElement._rlp_encode_bytes(b'sub4'),
            ))),
        ]
    )
    def test_var_db_check_prefix(self, score_db, is_v2, expected):
        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=is_v2)

        if is_v2:
            sep: bytes = b''
        else:
            sep: bytes = b'|'
        expected: bytes = sep.join((score_db.address.to_bytes(), expected))

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test_var'
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_var = VarDB(name, sub_db, value_type=bytes)

        def _get_context_db(score_db):
            return score_db._db._score_db._context_db

        _get_context_db(score_db).put = mock.Mock()

        test_var.set(value)

        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected

    @pytest.mark.parametrize(
        "is_v2,expected",
        [
            (False, b'|'.join((
                    b'sub1',
                    b'sub2',
                    b'sub3',
                    b'sub4',
                    b'key',
            ))),
            (True, b''.join((
                    KeyElement._rlp_encode_bytes(b'sub1'),
                    KeyElement._rlp_encode_bytes(b'sub2'),
                    KeyElement._rlp_encode_bytes(b'sub3'),
                    KeyElement._rlp_encode_bytes(b'sub4'),
                    KeyElement._rlp_encode_bytes(b'key'),
            ))),
        ]
    )
    def test_sub_db_check_prefix(self, score_db, is_v2, expected):
        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=is_v2)

        if is_v2:
            sep: bytes = b''
        else:
            sep: bytes = b'|'
        expected: bytes = sep.join((score_db.address.to_bytes(), expected))

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        key = b'key'
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)

        def _get_context_db(score_db):
            return score_db._db._score_db._context_db

        _get_context_db(score_db).put = mock.Mock()

        sub_db.put(key, value)

        args, _ = _get_context_db(score_db).put.call_args_list[0]
        assert args[1] == expected

    def test_dict_db_migration(self, score_db):

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test'
        key1 = b'aaaa'
        key2 = b'bbbb'
        key3 = b'cccc'
        key4 = b'dddd'
        value = b'value'
        depth = 4

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_db = DictDB(name, sub_db, value_type=bytes, depth=depth)
        test_db[key1][key2][key3][key4] = value
        assert value == test_db[key1][key2][key3][key4]

        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=True)

        test_db = DictDB(name, sub_db, value_type=bytes, depth=depth)
        assert value == test_db[key1][key2][key3][key4]

    def test_array_db_migration(self, score_db):
        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test'
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_db = ArrayDB(name, sub_db, value_type=bytes)
        test_db.put(value)
        assert value == test_db[0]

        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=True)

        test_db = ArrayDB(name, sub_db, value_type=bytes)
        assert value == test_db[0]

    def test_var_db_migration(self, score_db):
        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name = b'test'
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_db = VarDB(name, sub_db, value_type=bytes)
        test_db.set(value)
        assert value == test_db.get()

        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=True)

        test_db = VarDB(name, sub_db, value_type=bytes)
        assert value == test_db.get()

    def test_sub_db_migration(self, score_db):
        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        key = b'key'
        value = b'value'

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        sub_db.put(key, value)
        assert value == sub_db.get(key)

        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=True)

        assert value == sub_db.get(key)

    def test_conflict_container_db(self, score_db):
        type(score_db._db._score_db)._is_v2 = PropertyMock(return_value=True)
        def _get_context_db(score_db):
            return score_db._db._score_db._context_db
        _get_context_db(score_db).put = mock.Mock()

        sub1 = b'sub1'
        sub2 = b'sub2'
        sub3 = b'sub3'
        sub4 = b'sub4'

        name: bytes = b'test'
        key1 = b'aaaa'
        key2 = b'bbbb'
        key3 = b'cccc'
        key4 = b'dddd'
        value = b'value'
        depth: int = 4

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        test_dict = DictDB(key=name, db=sub_db, value_type=bytes, depth=depth)

        test_dict[key1][key2][key3][key4] = value

        expected = b''.join(
            (
                score_db.address.to_bytes(),
                DICT_DB_ID,
                KeyElement._rlp_encode_bytes(name),
                KeyElement._rlp_encode_bytes(sub1),
                KeyElement._rlp_encode_bytes(sub2),
                KeyElement._rlp_encode_bytes(sub3),
                KeyElement._rlp_encode_bytes(sub4),
                KeyElement._rlp_encode_bytes(key1),
                KeyElement._rlp_encode_bytes(key2),
                KeyElement._rlp_encode_bytes(key3),
                KeyElement._rlp_encode_bytes(key4)
            )
        )
        args, _ = _get_context_db(score_db).put.call_args_list[0]
        final_key1 = args[1]
        assert final_key1 == expected

        sub_db = score_db.get_sub_db(sub1)
        sub_db = sub_db.get_sub_db(sub2)
        sub_db = sub_db.get_sub_db(sub3)
        sub_db = sub_db.get_sub_db(sub4)
        name_db = sub_db.get_sub_db(prefix=name)
        depth_3_dict_db = DictDB(key=key1, db=name_db, value_type=bytes, depth=3)
        depth_3_dict_db[key2][key3][key4] = 2
        args, _ = _get_context_db(score_db).put.call_args_list[1]
        final_key2 = args[1]
        assert final_key2 != expected
