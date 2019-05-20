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
from iconservice.prep.candidate import Candidate
from iconservice.prep.candidate_container import CandidateSortedInfos, CandidateInfoMapper
from iconservice.prep.candidate_info_for_sort import CandidateInfoForSort
from tests import create_address


class TestPrepCandidate(unittest.TestCase):
    def test_prep_candidate(self):
        address: 'Address' = create_address()

        prep: 'Candidate' = Candidate(address)
        data: bytes = prep.to_bytes()
        actual_prep: 'Candidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)

        prep.name = "name"
        prep.email = "email"
        prep.website = "website"
        prep.json = "json"
        prep.target = "192.168.0.1"
        prep.block_height = 10
        prep.tx_index = 1000
        prep.gv.incentiveRep = 200

        data: bytes = prep.to_bytes()
        actual_prep: 'Candidate' = prep.from_bytes(data, address)
        self.assertEqual(prep, actual_prep)

    def _make_sorted_list(self,
                          count: int,
                          list1: list,
                          list2: list,
                          list3: list,
                          addresses: list) -> 'CandidateSortedInfos':
        mapper = CandidateInfoMapper()

        for i in range(count):
            addr: 'Address' = addresses[i]
            name: str = f'name{i}'
            total_delegated: int = list1[i]
            block_height: int = list2[i]
            tx_index: int = list3[i]
            info: 'CandidateInfoForSort' = CandidateInfoForSort(addr,
                                                                name,
                                                                block_height,
                                                                tx_index)
            info.update(total_delegated)
            mapper[addr] = info

        sorted_list: list = mapper.to_genesis_sorted_list()

        infos = CandidateSortedInfos()
        infos.genesis_update(sorted_list)
        return infos

    def test_prep_candidate_info_for_sort1(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort1_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(count, 0, -1)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [i for i in range(0, count)]
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [i for i in range(count, 0, -1)]
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort3(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(0, count)]

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort3_rev(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(count, 0, -1)]

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort4(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_update_info(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        info: 'CandidateInfoForSort' = CandidateInfoForSort(create_address(),
                                                                    "new_name1",
                                                            1,
                                                            1)
        infos.add_info(info)
        infos.update_info(info.address, count)
        self.assertEqual(info.name, infos.to_list()[0].name)

        infos.update_info(info.address, 0)
        self.assertEqual(info.name, infos.to_list()[count].name)

        for i in range(count):
            infos.update_info(info.address, count - i - 1)
            self.assertEqual(info.name, infos.to_list()[i + 1].name)

    def test_prep_candidate_info_for_updates(self):
        count = 5
        addresses = [create_address(), create_address(), create_address(), create_address(), create_address()]
        total_delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        infos = self._make_sorted_list(count, total_delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(infos.to_list()):
            infos.update_info(info.address, i)

        for i, info in enumerate(infos.to_list()):
            self.assertEqual(info.total_delegated, count - i - 1)

    def test_prep_candidate_info_for_sort(self):
        infos = CandidateSortedInfos()

        data_list: list = []
        data: tuple = (create_address(), "name0", 0, 0, 10)
        data_list.append(data)

        info: 'CandidateInfoForSort' = CandidateInfoForSort(data[0],
                                                            data[1],
                                                            data[2],
                                                            data[3])
        infos.add_info(info)
        infos.update_info(data[0], data[4])

        info = infos.to_list()[0]
        self.assertEqual(data[0], info.address)
        self.assertEqual(data[1], info.name)
        self.assertEqual(data[2], info.block_height)
        self.assertEqual(data[3], info.tx_index)
        self.assertEqual(data[4], info.total_delegated)

        # insert head
        data: tuple = (create_address(), "name1", 0, 0, 20)
        data_list.append(data)

        info: 'CandidateInfoForSort' = CandidateInfoForSort(data[0],
                                                            data[1],
                                                            data[2],
                                                            data[3])
        infos.add_info(info)
        infos.update_info(data[0], data[4])

        info = infos.to_list()[0]
        self.assertEqual(data[0], info.address)
        self.assertEqual(data[1], info.name)
        self.assertEqual(data[2], info.block_height)
        self.assertEqual(data[3], info.tx_index)
        self.assertEqual(data[4], info.total_delegated)

        # append
        data: tuple = (create_address(), "name2", 0, 0, 0)
        data_list.append(data)

        info: 'CandidateInfoForSort' = CandidateInfoForSort(data[0],
                                                            data[1],
                                                            data[2],
                                                            data[3])
        infos.add_info(info)
        infos.update_info(data[0], data[4])

        info = infos.to_list()[-1]
        self.assertEqual(data[0], info.address)
        self.assertEqual(data[1], info.name)
        self.assertEqual(data[2], info.block_height)
        self.assertEqual(data[3], info.tx_index)
        self.assertEqual(data[4], info.total_delegated)

        for data in data_list:
            infos.del_info(data[0])

        ret = infos.to_list()
        self.assertEqual(0, len(ret))


if __name__ == '__main__':
    unittest.main()
