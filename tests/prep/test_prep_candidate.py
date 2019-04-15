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
from iconservice.prep.prep_candidate_container import PRepCandidateSortedInfos, PRepCandiateInfoMapper
from iconservice.prep.prep_candidate_info_for_sort import PRepCandidateInfoForSort
from tests import create_address

from random import randint


class TestPrepCandidate(unittest.TestCase):
    def test_prep_candidate(self):
        address: 'Address' = create_address()

        prep: 'PRepCandidate' = PRepCandidate(address)
        data: bytes = prep.to_bytes()
        actual_prep: 'PRepCandidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)

        prep.name = "name"
        prep.email = "email"
        prep.website = "website"
        prep.json = "json"
        prep.ip = "192.168.0.1"
        prep.block_height = 10
        prep.tx_index = 1000
        prep.gv.incentiveRep = 200

        data: bytes = prep.to_bytes()
        actual_prep: 'PRepCandidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)

    def test_prep_candidate_info_for_sort(self):
        mapper = PRepCandiateInfoMapper()
        for i in range(5):
            addr: 'Address' = create_address()
            name: str = f'name{i}'
            total_delegated: int = randint(1, 10)
            block_height: int = randint(1, 10)
            tx_index: int = i
            info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(addr,
                                                                        name,
                                                                        block_height,
                                                                        tx_index)
            info.update(total_delegated)
            mapper[addr] = info

        sorted_list: list = mapper.to_genesis_sorted_list()

        infos = PRepCandidateSortedInfos()
        infos.genesis_update(sorted_list)
        self._custom_prt(infos.get())

        info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(create_address(),
                                                                    "new_name1",
                                                                    30,
                                                                    0)
        infos.add_info(info)
        infos.update_info(info.address, 50)
        self._custom_prt(infos.get())

        infos.update_info(info.address, 40)
        self._custom_prt(infos.get())

        infos.update_info(info.address, 5)
        self._custom_prt(infos.get())

        infos.update_info(info.address, 10)
        self._custom_prt(infos.get())

        infos.del_info(info.address)
        self._custom_prt(infos.get())

    def test_prep_candidate_info_for_sort2(self):
        mapper = PRepCandiateInfoMapper()

        total_delegatedes = [10, 8, 7, 7, 2]
        block_heights = [3, 10, 3, 4, 9]
        tx_indexes = [2, 0, 1, 4, 3]

        for i in range(5):
            addr: 'Address' = create_address()
            name: str = f'name{i}'
            total_delegated: int = total_delegatedes[i]
            block_height: int = block_heights[i]
            tx_index: int = tx_indexes[i]
            info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(addr,
                                                                        name,
                                                                        block_height,
                                                                        tx_index)
            info.update(total_delegated)
            mapper[addr] = info

        sorted_list: list = mapper.to_genesis_sorted_list()

        infos = PRepCandidateSortedInfos()
        infos.genesis_update(sorted_list)
        self._custom_prt(infos.get())

        info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(create_address(),
                                                                    "new_name1",
                                                                    30,
                                                                    0)
        infos.add_info(info)
        infos.update_info(info.address, 10)
        self._custom_prt(infos.get())

    def _custom_prt(self, infos: list):
        print("======")
        for info in infos:
            print(info.name, info.to_order_list())


if __name__ == '__main__':
    unittest.main()
