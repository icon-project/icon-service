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
import hashlib
import os

import pytest

from iconservice.base.address import AddressPrefix, Address
from iconservice.base.exception import InvalidParamsException
from iconservice.prep.validator import _validate_p2p_endpoint, _validate_prep_public_key, _validate_uri, _validate_email

NAME = "banana"
EMAIL = "banana@example.com"
WEBSITE = "https://banana.example.com"
DETAILS = "https://banana.example.com/details"
P2P_END_POINT = "https://banana.example.com:7100"
IREP = 10_000
BLOCK_HEIGHT = 777
TX_INDEX = 0


@pytest.fixture
def public_key_address_pair():
    public_key = os.urandom(32)
    address = Address(AddressPrefix.EOA, hashlib.sha3_256(public_key[1:]).digest()[-20:])

    return public_key, address


def test_validate_public_key(public_key_address_pair):
    public_key, address = public_key_address_pair
    try:
        _validate_prep_public_key(public_key, address)
    except BaseException:
        pytest.fail("validating public key test Failed")


def test_validate_public_key_invalid_case(public_key_address_pair):
    public_key, address = public_key_address_pair
    public_key = os.urandom(32)
    with pytest.raises(InvalidParamsException) as e:
        _validate_prep_public_key(public_key, address)
    assert e.value.message == 'Invalid publicKey'


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
                          'invalid.@asdf.com-', "email@domain..com", "invalid@abcd@abcd.com"]

    for email in invalid_email_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_email(email)
        assert e.value.message == "Invalid email format"

    valid_email = "valid@valid.com"
    try:
        _validate_email(valid_email)
    except BaseException:
        pytest.fail("Validating email test failed")
