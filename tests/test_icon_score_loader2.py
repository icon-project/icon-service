import unittest

from os import path, makedirs, symlink
from iconservice.iconscore.icon_score_base import IconScoreBase, Address
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_deployer import IconScoreInstaller
from iconservice.base.address import AddressPrefix, create_address
import inspect

TEST_ROOT_PATH = path.abspath(path.join(path.dirname(__file__), '../'))


class TestIconScoreLoader(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        self._score_path = path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self._loader = IconScoreLoader(self._score_path)
        self._addr_test_score01 = create_address(AddressPrefix.CONTRACT, b'test_score01')
        self._addr_test_score02 = create_address(AddressPrefix.CONTRACT, b'test_score02')

    def tearDown(self):
        remove_path = path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)
        remove_path = path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)
        pass

    @staticmethod
    def __ensure_dir(dir_path):
        if not path.exists(dir_path):
            makedirs(dir_path)

    def load_proj(self, proj: str, addr_score: Address) -> IconScoreBase:
        target_path = path.join(self._score_path, addr_score.body.hex())
        makedirs(target_path, exist_ok=True)
        target_path = path.join(target_path, '0_0')

        ref_path = path.join(TEST_ROOT_PATH, 'tests/tmp/{}'.format(proj))
        symlink(ref_path, target_path, target_is_directory=True)
        return self._loader.load_score(addr_score.body.hex())

    def test_install(self):
        self.__ensure_dir(self._score_path)

        score = self.load_proj('test_score01', self._addr_test_score01)
        print('test_score01', score.get_api())
        score = self.load_proj('test_score02', self._addr_test_score02)
        print('test_score02', score.get_api())

        self.assertTrue(IconScoreBase in inspect.getmro(score))
