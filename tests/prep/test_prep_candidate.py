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
from iconservice.prep.candidate_container import SortedCandidates, CandidateInfoMapper
from iconservice.prep.candidate import Candidate
from tests import create_address


class TestPrepCandidate(unittest.TestCase):
    def test_candidate_encode_decode(self):
        address: 'Address' = create_address()

        candidate: 'Candidate' = Candidate(address=address)
        data: bytes = candidate.to_bytes()
        actual: 'Candidate' = Candidate.from_bytes(address, data)
        self.assertEqual(candidate, actual)

        candidate: 'Candidate' = Candidate(address=address,
                                           name="name",
                                           email="email",
                                           website="website",
                                           json="json",
                                           ip="192.168.0.1",
                                           block_height=10,
                                           tx_index=1000,
                                           incentive_rep=200)

        data: bytes = candidate.to_bytes()
        actual: 'Candidate' = Candidate.from_bytes(address, data)
        self.assertEqual(candidate, actual)

    def test_candidate_encode_decode2(self):
        address: 'Address' = create_address()

        candidate: 'Candidate' = Candidate(address=address)
        data: bytes = candidate.to_bytes()
        actual: 'Candidate' = Candidate.from_bytes(address, data)
        self.assertEqual(candidate, actual)

        candidate: 'Candidate' = Candidate(address=address,
                                           name="name",
                                           email="email",
                                           website="website",
                                           json="json",
                                           ip="192.168.0.1",
                                           block_height=10,
                                           tx_index=1000,
                                           incentive_rep=200)

        data: bytes = candidate.to_bytes()
        actual: 'Candidate' = Candidate.from_bytes(address, data)
        self.assertEqual(candidate, actual)

    def _make_sorted_list(self,
                          count: int,
                          list1: list,
                          list2: list,
                          list3: list,
                          addresses: list) -> 'SortedCandidates':
        mapper = CandidateInfoMapper()

        for i in range(count):
            addr: 'Address' = addresses[i]
            name: str = f'name{i}'
            delegated: int = list1[i]
            block_height: int = list2[i]
            tx_index: int = list3[i]
            candidate: 'Candidate' = Candidate(address=addr,
                                               name=name,
                                               block_height=block_height,
                                               tx_index=tx_index)
            candidate.delegated = delegated
            mapper[addr] = candidate

        sorted_list: list = mapper.to_genesis_sorted_list()

        infos = SortedCandidates()
        infos.genesis_update(sorted_list)
        return infos

    def test_prep_candidate_info_for_sort1(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort1_rev(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [i for i in range(count, 0, -1)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [i for i in range(0, count)]
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort2_rev(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [i for i in range(count, 0, -1)]
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort3(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(0, count)]

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_sort3_rev(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [i for i in range(count, 0, -1)]

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{count - i - 1}', info.name)

    def test_prep_candidate_info_for_sort4(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(f'name{i}', info.name)

    def test_prep_candidate_info_for_update_info(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [i for i in range(0, count)]
        block_heights = [0] * count
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        candidate: 'Candidate' = Candidate(address=create_address(),
                                           name="new_name1",
                                           block_height=1,
                                           tx_index=1)
        candidates.add_candidate(candidate)
        candidates.update_candidate(candidate.address, count)
        self.assertEqual(candidate.name, candidates.to_list()[0].name)

        candidates.update_candidate(candidate.address, 0)
        self.assertEqual(candidate.name, candidates.to_list()[count].name)

        for i in range(count):
            candidates.update_candidate(candidate.address, count - i - 1)
            self.assertEqual(candidate.name, candidates.to_list()[i + 1].name)

    def test_prep_candidate_info_for_updates(self):
        count = 5
        addresses = [create_address() for _ in range(count)]
        delegateds = [0] * count
        block_heights = [0] * count
        tx_indexs = [0] * count

        candidates = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)

        for i, candidate in enumerate(candidates.to_list()):
            candidates.update_candidate(candidate.address, i)

        for i, info in enumerate(candidates.to_list()):
            self.assertEqual(info.delegated, count - i - 1)

    def test_prep_candidate_info_for_sort(self):
        candidates = SortedCandidates()

        data_list: list = []
        data: tuple = (create_address(), "name0", 0, 0, 10)
        data_list.append(data)

        candidate: 'Candidate' = Candidate(address=data[0],
                                           name=data[1],
                                           block_height=data[2],
                                           tx_index=data[3])
        candidates.add_candidate(candidate)
        candidates.update_candidate(data[0], data[4])

        actual = candidates.to_list()[0]
        self.assertEqual(data[0], actual.address)
        self.assertEqual(data[1], actual.name)
        self.assertEqual(data[2], actual.block_height)
        self.assertEqual(data[3], actual.tx_index)
        self.assertEqual(data[4], actual.delegated)

        # insert head
        data: tuple = (create_address(), "name1", 0, 0, 20)
        data_list.append(data)

        candidate: 'Candidate' = Candidate(address=data[0],
                                           name=data[1],
                                           block_height=data[2],
                                           tx_index=data[3])
        candidates.add_candidate(candidate)
        candidates.update_candidate(data[0], data[4])

        actual = candidates.to_list()[0]
        self.assertEqual(data[0], actual.address)
        self.assertEqual(data[1], actual.name)
        self.assertEqual(data[2], actual.block_height)
        self.assertEqual(data[3], actual.tx_index)
        self.assertEqual(data[4], actual.delegated)

        # append
        data: tuple = (create_address(), "name2", 0, 0, 0)
        data_list.append(data)

        candidate: 'Candidate' = Candidate(address=data[0],
                                           name=data[1],
                                           block_height=data[2],
                                           tx_index=data[3])
        candidates.add_candidate(candidate)
        candidates.update_candidate(data[0], data[4])

        actual = candidates.to_list()[-1]
        self.assertEqual(data[0], actual.address)
        self.assertEqual(data[1], actual.name)
        self.assertEqual(data[2], actual.block_height)
        self.assertEqual(data[3], actual.tx_index)
        self.assertEqual(data[4], actual.delegated)

        for data in data_list:
            candidates.del_candidate(data[0])

        ret = candidates.to_list()
        self.assertEqual(0, len(ret))

    # def test_speed(self):
    #     count = 3000
    #     addresses = [create_address() for _ in range(count)]
    #     delegateds = [i for i in range(count)]
    #     block_heights = [i for i in range(count)]
    #     tx_indexs = [i for i in range(count)]
    #
    #     infos = self._make_sorted_list(count, delegateds, block_heights, tx_indexs, addresses)
    #
    #     data: tuple = (create_address(), "name0", 0, 0, 0)
    #     info: 'CandidateInfoForSort' = CandidateInfoForSort(data[0],
    #                                                         data[1],
    #                                                         data[2],
    #                                                         data[3])
    #     infos.add_info(info)
    #     for i in range(count):
    #         infos.update_info(data[0], i)
    #
    #     for i in range(count, 0, -1):
    #         infos.update_info(data[0], i)


if __name__ == '__main__':
    unittest.main()
