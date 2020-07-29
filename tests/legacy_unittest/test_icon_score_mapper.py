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
from unittest.mock import Mock

from iconservice.deploy import DeployStorage
from iconservice.iconscore.icon_score_base import IconScoreBase
from iconservice.score_loader.icon_score_class_loader import IconScoreClassLoader
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_mapper import IconScoreMapper


class TestIconScoreMapper(unittest.TestCase):
    def setUp(self):
        IconScoreMapper.icon_score_class_loader = Mock(spec=IconScoreClassLoader)
        IconScoreMapper.deploy_storage = Mock(spec=DeployStorage)
        self.context = Mock(spec=IconScoreContext)
        self.icon_score_mapper = IconScoreMapper()

    def tearDown(self):
        pass

    # def test_get_icon_score_score_success(self):
    #     tx_hash = create_tx_hash()
    #     self.icon_score_mapper.load_score = Mock(return_value=TestScore())
    #     self.icon_score_mapper.get_icon_score(create_address(AddressPrefix.CONTRACT), tx_hash)


class TestScore(IconScoreBase):

    def __init__(self):
        pass

    def on_install(self):
        pass

    def on_update(self):
        pass
