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

import unittest

from iconservice.base.address import Address, AddressPrefix
from iconservice.prep.prep_address_converter import PRepAddressConverter


class TestPRepAddressConverter(unittest.TestCase):
    def setUp(self) -> None:
        self.converter = PRepAddressConverter()
        self.node_addresses = []
        self.prep_addresses = []

        # Generate sample addresses for test
        for i in range(10):
            node_address = Address.from_data(AddressPrefix.EOA, f'node_address{i}'.encode("utf-8"))
            prep_address = Address.from_data(AddressPrefix.EOA, f'prep_address{i}'.encode("utf-8"))

            self.node_addresses.append(node_address)
            self.prep_addresses.append(prep_address)

    def test_add_node_address(self):
        node_address = self.node_addresses[0]
        prep_address = self.prep_addresses[0]

        # In case when a given node address is not added
        address = self.converter.get_prep_address_from_node_address(node_address)
        assert address == node_address

        # In case when a given node address is added
        self.converter.add_node_address(node_address, prep_address)
        address = self.converter.get_prep_address_from_node_address(node_address)
        assert address == prep_address

        self.converter._delete_node_address(node_address)
        address = self.converter.get_prep_address_from_node_address(node_address)
        assert address == node_address
        assert address != prep_address

    def test_replace_node_address(self):
        converter = self.converter

        old_node_address = self.node_addresses[0]
        new_node_address = self.node_addresses[1]
        prep_address = self.prep_addresses[0]

        # Confirm that 3 addresses are different
        assert old_node_address != new_node_address
        assert old_node_address != prep_address
        assert new_node_address != prep_address

        # Check whether old_node_address is not added to converter
        address = self.converter.get_prep_address_from_node_address(old_node_address)
        assert address == old_node_address

        # Add old_node_address
        converter.add_node_address(old_node_address, prep_address)
        address = self.converter.get_prep_address_from_node_address(old_node_address)
        assert address == prep_address

        # Replace old_node_address with a new node_address
        converter.replace_node_address(new_node_address, prep_address, old_node_address)
        assert prep_address == converter.get_prep_address_from_node_address(old_node_address)
        assert prep_address == converter.get_prep_address_from_node_address(new_node_address)
        assert old_node_address in converter._prev_node_address_mapper
        assert new_node_address in converter._node_address_mapper
        assert len(converter._prev_node_address_mapper) == 1
        assert len(converter._node_address_mapper) == 1

    def test_delete_node_address(self):
        converter = self.converter
        node_address = self.node_addresses[0]
        prep_address = self.prep_addresses[0]

        # Confirm that 2 addresses are different
        assert node_address != prep_address

        # Check whether old_node_address is not added to converter
        address = self.converter.get_prep_address_from_node_address(node_address)
        assert address == node_address

        # Add old_node_address
        converter.add_node_address(node_address, prep_address)

        converter.delete_node_address(node_address, prep_address)
        address = converter.get_prep_address_from_node_address(node_address)
        assert address == prep_address
        assert len(converter._prev_node_address_mapper) == 1
        assert len(converter._node_address_mapper) == 0

    def test_copy(self):
        converter = self.converter
        old_node_address = self.node_addresses[0]
        new_node_address = self.node_addresses[1]
        prep_address = self.prep_addresses[0]

        # Add old_node_address
        converter.add_node_address(old_node_address, prep_address)
        address = self.converter.get_prep_address_from_node_address(old_node_address)
        assert address == prep_address

        # Replace old_node_address with a new node_address
        converter.replace_node_address(new_node_address, prep_address, old_node_address)

        new_converter = converter.copy()
        assert isinstance(new_converter, PRepAddressConverter)
        assert prep_address == new_converter.get_prep_address_from_node_address(old_node_address)
        assert prep_address == new_converter.get_prep_address_from_node_address(new_node_address)
        assert old_node_address in new_converter._prev_node_address_mapper
        assert new_node_address in new_converter._node_address_mapper
        assert len(new_converter._prev_node_address_mapper) == 1
        assert len(new_converter._node_address_mapper) == 1
        assert id(new_converter._prev_node_address_mapper) != id(converter._prev_node_address_mapper)
        assert id(new_converter._node_address_mapper) != id(converter._node_address_mapper)

        new_converter._delete_node_address(new_node_address)
        assert new_node_address == new_converter.get_prep_address_from_node_address(new_node_address)
        assert prep_address == converter.get_prep_address_from_node_address(new_node_address)

        new_converter.reset_prev_node_address()
        assert old_node_address == new_converter.get_prep_address_from_node_address(old_node_address)
        assert prep_address == converter.get_prep_address_from_node_address(old_node_address)

    def test_serialize(self):
        # empty
        data: bytes = PRepAddressConverter().to_bytes()
        converter: 'PRepAddressConverter' = PRepAddressConverter.from_bytes(data)
        assert self.converter._prev_node_address_mapper == converter._prev_node_address_mapper

        # add data
        old_node_address = self.node_addresses[0]
        new_node_address = self.node_addresses[1]
        prep_address = self.prep_addresses[0]

        self.converter.replace_node_address(old_node_address, prep_address, new_node_address)
        data: bytes = self.converter.to_bytes()
        converter: 'PRepAddressConverter' = PRepAddressConverter.from_bytes(data)
        assert self.converter._prev_node_address_mapper == converter._prev_node_address_mapper


if __name__ == '__main__':
    unittest.main()
