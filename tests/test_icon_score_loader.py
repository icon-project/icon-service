import unittest
import os
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.base.address import AddressPrefix, create_address


class TestIconScoreLoader(unittest.TestCase):
    def setUp(self):
        self._loader = IconScoreLoader('test_score')
        self._address = create_address(AddressPrefix.CONTRACT, b'test')
        self._dir_list = ['3_0', '3_3', '5_1', ]
        pass

    def tearDown(self):
        pass

    def test_load(self):
        score = self._loader.load_score(self._address)
