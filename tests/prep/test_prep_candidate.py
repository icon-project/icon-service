#!/usr/bin/env python3
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


import unittest

from iconservice import Address
from iconservice.prep.prep_candidate import PRepCandidate
from tests import create_address


class TestPrepCandidate(unittest.TestCase):
    def test_prep_candidate(self):
        address: 'Address' = create_address()

        prep: 'PRepCandidate' = PRepCandidate(address)
        data: bytes = prep.to_bytes()
        actual_prep: 'PRepCandidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)

        prep.network_info = "network_info"
        prep.name = "name"
        prep.url = "url"
        prep.block_height = 10
        prep.timestamp = 2000
        prep.governance.incentiveRep = 200

        prep: 'PRepCandidate' = PRepCandidate(address)
        data: bytes = prep.to_bytes()
        actual_prep: 'PRepCandidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)


if __name__ == '__main__':
    unittest.main()
