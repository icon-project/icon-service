# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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

import json
import os.path

import pytest

from iconservice.icon_config import ConfigSanityChecker, default_icon_config, check_config


@pytest.fixture(scope="function")
def get_default_conf():
    def func(value):
        return {"a": value, "dict": {"a": value}}
    return func


@pytest.fixture(scope="function", params=["iconservice.json"])
def conf(request):
    path: str = os.path.join(os.path.dirname(__file__), request.param)
    with open(path, mode="rt") as f:
        return json.loads(f.read())


class TestConfigSanityChecker(object):
    @pytest.mark.parametrize("value", [True, 1.1, 2, "hello"])
    def test_run_with_simple_params(self, get_default_conf, value):
        default_conf = get_default_conf(value)
        confs = [
            {"a": value},
            {"dict": {"a": value}},
            {"a": value, "dict": {"a": value}},
        ]

        checker = ConfigSanityChecker(default_conf)
        for conf in confs:
            assert checker.run(conf) is True
            assert len(checker.invalid_keys) == 0
            assert len(checker.invalid_values) == 0

    @pytest.mark.parametrize("value", [True, 1.1, 2, "hello"])
    def test_run_with_no_key(self, get_default_conf, value):
        default_conf = get_default_conf(value)
        confs = [
            {"b": value},
            {"dict": {"b": value}},
            {"b": value, "dict": {"b": value}},
        ]

        checker = ConfigSanityChecker(default_conf)
        for conf in confs:
            assert checker.run(conf) is True
            assert len(checker.invalid_keys) > 0
            assert len(checker.invalid_values) == 0

    @pytest.mark.parametrize("value", [True, 1.1, 2, "hello"])
    def test_run_with_invalid_value(self, get_default_conf, value):
        default_conf = get_default_conf(value)
        confs = [
            {"a": bytes(4)},
            {"dict": {"a": bytes(4)}},
            {"a": 0, "dict": {"a": "hello"}},
        ]

        checker = ConfigSanityChecker(default_conf)
        for conf in confs:
            assert checker.run(conf) is False
            assert len(checker.invalid_keys) == 0
            assert len(checker.invalid_values) in (1, 2)

    def test_run_with_iconservice_json(self, conf):
        """Test ConfigSanityChecker with iconservice.json contained in docker image
        """
        # Test 1 - Success
        checker = ConfigSanityChecker(default_icon_config)
        ret = checker.run(conf)

        assert ret is True
        assert len(checker.invalid_values) == 0

        # invalid keys: "deployWhitelist", "colorLog
        # checker.run() returns True regardless of the number of invalid keys
        assert len(checker.invalid_keys) == 2

        # Sorting is just used for testing convenience
        invalid_keys = sorted([item.key for item in checker.invalid_keys])
        assert invalid_keys == ["colorLog", "deployerWhiteList"]

        # Test 2 - Failure
        # Invalid value makes checker.run() return False
        # Add invalid keys and values
        conf["a"] = 0  # invalid key
        conf["service"]["a"] = "hello"  # invalid key
        conf["channel"] = True  # invalid value

        ret = checker.run(conf)
        assert ret is False
        assert len(checker.invalid_keys) == 4
        # Sorting is just used for testing convenience
        invalid_keys = sorted([item.key for item in checker.invalid_keys])
        assert invalid_keys == ["a", "a", "colorLog", "deployerWhiteList"]
        invalid_values = checker.invalid_values
        assert len(invalid_values) == 1
        assert invalid_values[0].key == "channel"

    def test_check_config(self, conf):
        ret = check_config(conf, default_icon_config)
        assert ret is True
