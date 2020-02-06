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
from typing import List

import pytest

from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import Revision
from iconservice.prep.validator import _validate_p2p_endpoint
from iconservice.prep.validator import _validate_uri, _validate_email, _validate_country

NAME = "banana"
EMAIL = "banana@example.com"
WEBSITE = "https://banana.example.com"
DETAILS = "https://banana.example.com/details"
P2P_END_POINT = "https://banana.example.com:7100"
IREP = 10_000
BLOCK_HEIGHT = 777
TX_INDEX = 0


def test_validate_uri():
    invalid_uri_list = ["http://", "http://.", "http://..", "http://../", "http://?", "http://??", "http://??/",
                        "http://#", "http://##", "http://##/", "http://foo.bar?q=Spaces should be encoded",
                        "//", "//a", "///a", "///", "http:///a", "foo.com", "rdar://1234", "h://test",
                        "http:// shouldfail.com", "http://foo.bar/foo(bar)baz quux", "ftps://foo.bar/",
                        "http://-error-.invalid/", "http://-a.b.co", "http://a.b-.co", "http://3628126748",
                        "http://.www.foo.bar/", "http://www.foo.bar./", "http://.www.foo.bar./",
                        "http://022.107.254.1"]

    valid_uri_list = ["http://foo.com/blah_blah", "http://foo.com/blah_blah/", "http://foo.com/blah_blah_(wikipedia)",
                      "http://foo.com/blah_blah_(wikipedia)_(again)", "http://www.example.com/wpstyle/?p=364",
                      "https://www.example.com/foo/?bar=baz&inga=42&quux", "http://odf.ws/123",
                      "http://foo.com/blah_(wikipedia)#cite-1", "http://foo.com/blah_(wikipedia)_blah#cite-1",
                      "http://foo.com/unicode_(✪)_in_parens", "http://foo.com/(something)?after=parens",
                      "http://code.google.com/events/#&product=browser", "http://foo.bar/?q=Test%20URL-encoded%20stuff",
                      "http://1337.net", "http://223.255.255.254", "http://foo.bar:8080", "https://foo.bar:8000",
                      "https://192.10.2.3:1234", "https://localhost:1234", "http://localhost:1234", "http://localhost",
                      "https://localhost"]
    for uri in invalid_uri_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_uri(uri)
        assert e.value.message == 'Invalid uri format'

    for uri in valid_uri_list:
        try:
            _validate_uri(uri)
        except BaseException:
            pytest.fail("validating uri test Failed")


def test_validate_endpoint():
    invalid_endpoint_list = ["http://", "http://.", "http://..", "http://../", "http://?", "http://??", "http://??/",
                             "http://#", "http://##", "http://##/", "http://foo.bar?q=Spaces should be encoded",
                             "//", "//a", "///a", "///", "http:///a", "foo.com", "rdar://1234", "h://test",
                             "http:// shouldfail.com", "http://foo.bar/foo(bar)baz quux", "ftps://foo.bar/",
                             "http://-error-.invalid/", "http://-a.b.co", "http://a.b-.co", "http://0.0.0.0:8080",
                             "http://3628126748", "http://.www.foo.bar/", "http://www.foo.bar./",
                             "http://.www.foo.bar./", "http://:8080", "http://.:8080", "http://..:8080",
                             "http://../:8080", "http://?:8080", "http://??:8080", "http://??/:8080", "http://#:8080",
                             "http://##:8080", "http://##/:8080", "http://foo.bar?q=Spaces should be encoded:8080",
                             "//:8080", "//a:8080", "///a:8080", "///:8080", "http:///a:8080", "rdar://1234:8080",
                             "h://test:8080", "http:// shouldfail.com:8080",  "http://foo.bar/foo(bar)baz quux:8080",
                             "ftps://foo.bar/:8080", "http://-error-.invalid/:8080", "http://-a.b.co:8080",
                             "http://a.b-.co:8080", "http://3628126748:8080", "http://.www.foo.bar/:8080",
                             "http://www.foo.bar./:8080", "http://.www.foo.bar./:8080", "022.107.254.1:8080",
                             "256.123.1.1:8000"]

    valid_endpoint_list = ["foo.com:1", "192.10.6.2:8000", "localhost:1234"]
    for endpoint in invalid_endpoint_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_p2p_endpoint(endpoint)

    for endpoint in valid_endpoint_list:
        try:
            _validate_p2p_endpoint(endpoint)
        except BaseException:
            pytest.fail("validating endpoint test Failed")


def test_validate_email():
    invalid_email_list = ['invalid email', 'invalid.com', 'invalid@', 'invalid@a', 'invalid@a.', 'invalid@.com',
                          'invalid.@asdf.com-', "email@domain..com", "invalid@abcd@abcd.com",
                          'john..doe@example.com', ".invalid@email.com"]

    for email in invalid_email_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_email(Revision.DECENTRALIZATION.value, email)
        assert e.value.message == "Invalid email format"

    valid_email_list = ['example@localhost', 'user@email.com']
    for email in valid_email_list:
        try:
            _validate_email(Revision.DECENTRALIZATION.value, email)
        except BaseException:
            pytest.fail("Validating email test failed")


def test_validate_fixed_email():
    invalid_email_list = ['invalid email', 'invalid.com', 'invalid@', f"{'a'*65}@example.com",
                          f"{'a'*253}@aa"]

    for email in invalid_email_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_email(Revision.FIX_EMAIL_REGEX.value, email)
        assert e.value.message == "Invalid email format"

    valid_email_list = ['example@localhost', 'user@email.com', f'{"a"*63}@example.com',
                        f"{'a'*64}@{'b'*189}", '\\@example.com', 'a@a']
    for email in valid_email_list:
        try:
            _validate_email(Revision.FIX_EMAIL_REGEX.value, email)
        except BaseException:
            pytest.fail("Validating email test failed")


def test_validate_country():
    valid_country_codes: List[str] = ["KOR", "USA", "CHN", "JPN", "FRA", "RUS", "DEU", "CAN"]
    invalid_country_codes: List[str] = ["123", "hello", "KR", "US", "CA", "FR"]

    for code in valid_country_codes:
        _validate_country(code)
        _validate_country(code.lower())

    for code in invalid_country_codes:
        with pytest.raises(InvalidParamsException):
            _validate_country(code)
        with pytest.raises(InvalidParamsException):
            _validate_country(code.lower())
