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

    def _make_sorted_list(self,
                          count: int,
                          list1: list,
                          list2: list,
                          list3: list,
                          addresses: list) -> 'PRepCandidateSortedInfos':
        mapper = PRepCandiateInfoMapper()

        for i in range(count):
            addr: 'Address' = addresses[i]
            name: str = f'name{i}'
            total_delegated: int = list1[i]
            block_height: int = list2[i]
            tx_index: int = list3[i]
            info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(addr,
                                                                        name,
                                                                        block_height,
                                                                        tx_index)
            info.update(total_delegated)
            mapper[addr] = info

        sorted_list: list = mapper.to_genesis_sorted_list()

        infos = PRepCandidateSortedInfos()
        infos.genesis_update(sorted_list)
        return infos

    def test_prep_candidate_info_for_sort1(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort1_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(count, 0, -1)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [i for i in range(0, count)]
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [i for i in range(count, 0, -1)]
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort3(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(0, count)]

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort3_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(count, 0, -1)]

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort4(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_update_info(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        info: 'PRepCandidateInfoForSort' = PRepCandidateInfoForSort(create_address(),
                                                                    "new_name1",
                                                                    1,
                                                                    1)
        infos.add_info(info)
        infos.update_info(info.address, count)
        self.assertEqual(info.name, infos.get()[0].name)

        infos.update_info(info.address, 0)
        self.assertEqual(info.name, infos.get()[count].name)

        for i in range(count):
            infos.update_info(info.address, count - i - 1)
            self.assertEqual(info.name, infos.get()[i + 1].name)

    def test_prep_candidate_info_for_updates(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.get()):
            infos.update_info(info.address, i)

        for i, info in enumerate(infos.get()):
            self.assertEqual(info.total_delegated, count - i - 1)


if __name__ == '__main__':
    unittest.main()
