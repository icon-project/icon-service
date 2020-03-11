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

from iconservice.base.address import MalformedAddress, AddressPrefix


def test_from_string():
    address = MalformedAddress.from_string('')
    assert address.prefix == AddressPrefix.EOA
    assert address.body == b''
    assert str(address) == 'hx'

    short_address_without_hx = MalformedAddress.from_string('123124124125')
    assert short_address_without_hx.prefix == AddressPrefix.EOA
    assert str(short_address_without_hx) == 'hx123124124125'
    assert short_address_without_hx.body == bytes.fromhex('123124124125')

    text = 'bf85fac2d1b507a2db9ce9526e6d91476f16a2d269f51636f9c4b2d512017faf'
    long_address_without_hx = MalformedAddress.from_string(text)
    assert long_address_without_hx.prefix == AddressPrefix.EOA
    assert str(long_address_without_hx) == f'hx{text}'
    assert  long_address_without_hx.body == bytes.fromhex(text)

    long_address = MalformedAddress.from_string(f'hx{text}')
    assert long_address == long_address_without_hx

    text = 'hxa23651905d221dd36b'
    short_address = MalformedAddress.from_string(text)
    assert short_address.prefix == AddressPrefix.EOA
    assert str(short_address) == text
    assert short_address.body == bytes.fromhex('a23651905d221dd36b')

