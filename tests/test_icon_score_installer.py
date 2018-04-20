import unittest
from icon.iconservice.iconscore.icon_score_installer import *
from icon.iconservice.base.address import Address


class TestICONSCOREINSTALLER(unittest.TestCase):
    def setUp(self):

        self.installer = IconScoreInstaller('/Users/lp1709no01/Desktop/')
        self.address = Address('cx', bytes.fromhex("1234123412341234123412341234123412341234"))
        self.archive_path = "/Users/lp1709no01/Desktop/ziptest/abcd.zip"
        self.install_path = os.path.join(self.installer.icon_score_root_path, str(self.address))
        self.test_directory_path = os.path.join(self.installer.icon_score_root_path, 'a')

    def test_write_zipfile_with_bytes(self):
        write_file_first_time_result = self.installer.write_zipfile_with_bytes(self.install_path
                                                                               , self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertTrue(os.path.isfile(self.install_path+".zip"))
        write_file_second_time_result = self.installer.write_zipfile_with_bytes(self.install_path+".zip"
                                                                                , self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_FILE_EXISTS_ERROR__CODE, write_file_second_time_result)

        self.installer.remove_exists_archive(self.install_path+".zip")

        write_file_with_exist_directory_path =\
            self.installer.write_zipfile_with_bytes(self.test_directory_path
                                                    , self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_IS_A_DIRECTORY_ERROR_CODE, write_file_with_exist_directory_path)

        write_file_with_unauthorized_path_result = \
            self.installer.write_zipfile_with_bytes('/', self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_PERMISSION_ERROR_CODE, write_file_with_unauthorized_path_result)

    def test_remove_exists_archive(self):
        self.installer.write_zipfile_with_bytes(self.install_path
                                                , self.installer.read_zipfile_as_byte(self.archive_path))
        self.installer.remove_exists_archive(self.install_path+".zip")
        self.assertFalse(os.path.isfile(self.install_path+".zip"))

    def test_extract_files(self):
        pass


if __name__ == "__main__":
    unittest.main()