import unittest
import os
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_installer import IconScoreInstaller
from iconservice.base.address import AddressPrefix, create_address


TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreLoader(unittest.TestCase):
    _ROOT_SCORE_PATH = os.path.join(TEST_ROOT_PATH, 'score')

    def setUp(self):
        self._loader = IconScoreLoader(self._ROOT_SCORE_PATH)
        self._address = create_address(AddressPrefix.CONTRACT, b'SampleToken')
        print(self._address)
        archive_path = 'tests/score.zip'
        archive_path = os.path.join(TEST_ROOT_PATH, archive_path)
        zip_bytes = self.read_zipfile_as_byte(archive_path)
        install_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self.__unpack_zip_file(install_path, zip_bytes)

    def tearDown(self):
        remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    @staticmethod
    def __unpack_zip_file(install_path: str, data: bytes):
        file_info_generator = IconScoreInstaller.extract_files_gen(data)
        for name, file_info, parent_directory in file_info_generator:
            if not os.path.exists(os.path.join(install_path, parent_directory)):
                os.makedirs(os.path.join(install_path, parent_directory))
            with file_info as file_info_context, open(os.path.join(install_path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)
        return True

    def test_install(self):
        score = self._loader.load_score(self._address.body.hex())
        self.assertNotEqual(score, None)
