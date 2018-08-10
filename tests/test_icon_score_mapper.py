# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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
from unittest.mock import Mock

from iconservice import InvalidParamsException, IconScoreBase
from iconservice.base.address import AddressPrefix
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from tests import create_address, create_tx_hash


class TestIconScoreMapper(unittest.TestCase):
    def setUp(self):
        IconScoreMapper.icon_score_loader = Mock(spec=IconScoreLoader)
        IconScoreMapper.deploy_storage = Mock(spec=IconScoreDeployStorage)
        self.context = Mock(spec=IconScoreContext)
        self.icon_score_mapper = IconScoreMapper()

    def tearDown(self):
        pass

    def test_get_icon_score_tx_hash_is_none(self):
        IconScoreMapper.deploy_storage.is_score_active = Mock(return_value=False)
        IconScoreMapper.deploy_storage.get_current_tx_hash = Mock(return_value=None)

        self.assertRaises(InvalidParamsException,
                          self.icon_score_mapper.get_icon_score, self.context, create_address(AddressPrefix.EOA))

    def test_get_icon_score_score_is_none_inactive(self):
        IconScoreMapper.deploy_storage.is_score_active = Mock(return_value=False)
        IconScoreMapper.deploy_storage.get_current_tx_hash = Mock(return_value=create_tx_hash())
        self.icon_score_mapper._load_score = Mock(return_value=None)

        self.assertRaises(InvalidParamsException,
                          self.icon_score_mapper.get_icon_score, self.context, create_address(AddressPrefix.EOA))

    def test_get_icon_score_score_is_none_active(self):
        IconScoreMapper.deploy_storage.is_score_active = Mock(return_value=True)
        IconScoreMapper.deploy_storage.get_current_tx_hash = Mock(return_value=create_tx_hash())
        self.icon_score_mapper._load_score = Mock(return_value=None)

        self.assertRaises(InvalidParamsException,
                          self.icon_score_mapper.get_icon_score, self.context, create_address(AddressPrefix.EOA))

    def test_get_icon_score_score_success(self):
        IconScoreMapper.deploy_storage.is_score_active = Mock(return_value=True)
        IconScoreMapper.deploy_storage.get_current_tx_hash = Mock(return_value=create_tx_hash())
        self.icon_score_mapper._load_score = Mock(return_value=TestScore())
        self.icon_score_mapper.get_icon_score(self.context, create_address(AddressPrefix.EOA))


class TestScore(IconScoreBase):

    def __init__(self):
        pass

    def on_install(self, **kwargs):
        pass

    def on_update(self, **kwargs):
        pass