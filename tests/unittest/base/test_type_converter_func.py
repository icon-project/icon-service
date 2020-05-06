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

from iconservice.base.address import Address
from iconservice.base.type_converter import TypeConverter
from tests import create_address


class TestScore:
    def func_param_int(self, value: int) -> int:
        return value

    def func_param_str(self, value: str) -> str:
        print(value)
        return value

    def func_param_bytes(self, value: bytes) -> bytes:
        return value

    def func_param_bool(self, value: bool) -> bool:
        return value

    def func_param_address1(self, value: Address) -> Address:
        return value

    def func_param_address2(self, value: "Address") -> "Address":
        return value


TEST_SCORE = TestScore()


def test_func_param_int():
    value = 1
    params = {"value": hex(value)}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_int)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_int(**params)


def test_func_param_str():
    value = "a"
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_str)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_str(**params)


def test_func_param_bytes():
    value = b"bytes"
    params = {"value": bytes.hex(value)}
    annotations = TypeConverter.make_annotations_from_method(
        TEST_SCORE.func_param_bytes
    )
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_bytes(**params)


def test_func_param_bool():
    value = True
    params = {"value": hex(int(value))}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_bool)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_bool(**params)


def test_func_param_address1():
    value = create_address()
    params = {"value": str(value)}
    annotations = TypeConverter.make_annotations_from_method(
        TEST_SCORE.func_param_address1
    )
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_address1(**params)


def test_func_param_address2():
    value = create_address()
    params = {"value": str(value)}
    annotations = TypeConverter.make_annotations_from_method(
        TEST_SCORE.func_param_address2
    )
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_address2(**params)


def test_func_param_int_none():
    value = None
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_int)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_int(**params)


def test_func_param_str_none():
    value = None
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_str)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_str(**params)


def test_func_param_bytes_none():
    value = None
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(
        TEST_SCORE.func_param_bytes
    )
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_bytes(**params)


def test_func_param_bool_none():
    value = None
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(TEST_SCORE.func_param_bool)
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_bool(**params)


def test_func_param_address_none():
    value = None
    params = {"value": value}
    annotations = TypeConverter.make_annotations_from_method(
        TEST_SCORE.func_param_address1
    )
    TypeConverter.convert_data_params(annotations, params)
    assert value == TEST_SCORE.func_param_address1(**params)
