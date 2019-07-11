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
    invalid_website_list = ['invalid website', 'invalid.com', 'http://c.com',
                            'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid.",
                            "https://abcd.com:812345", "http://abcd.com:812345", "http://asdf.aa-"]

    valid_website_list = ['https://valid.com:8080', 'http://valid.com:8080', 'http://valid.com:8080/asdf',
                          'https://valid.com:8080/abcd']

    for uri in invalid_website_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_uri(uri)
        assert e.value.message == 'Invalid uri format'

    for uri in valid_website_list:
        try:
            _validate_uri(uri)
        except BaseException:
            pytest.fail("validating uri test Failed")


def test_validate_endpoint():
    invalid_endpoint_list = ['invalid website', 'invalid.com', 'http://c.com',
                             'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid.",
                             "https://123.123.123.123:8080", "https://abcd.com:812345",
                             "http://abcd.com:812345", "http://asdf.aa-", "https://invalid.com:8080",
                             "http://invalid.com:8080", "invalid.com:abcd",
                             ]

    valid_endpoint_list = ['valid.com:8080', '123.222.134.255:8080']

    for endpoint in invalid_endpoint_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_p2p_endpoint(endpoint)
        assert e.value.message == "Invalid endpoint format" or e.value.message.startswith("Invalid port value")

    for endpoint in valid_endpoint_list:
        try:
            _validate_p2p_endpoint(endpoint)
        except BaseException:
            pytest.fail("validating endpoint test Failed")


def test_validate_email():
    invalid_email_list = ['invalid email', 'invalid.com', 'invalid@', 'invalid@a', 'invalid@a.', 'invalid@.com',
                          'invalid.@asdf.com-']

    for email in invalid_email_list:
        with pytest.raises(InvalidParamsException) as e:
            _validate_email(email)
        assert e.value.message == "Invalid email format"

    valid_email = "valid@valid.com"
    try:
        _validate_email(valid_email)
    except BaseException:
        pytest.fail("Validating email test failed")
