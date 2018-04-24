import unittest
from icon.iconservice.iconscore.icon_score_installer import *
from icon.iconservice.base.address import Address


class TestICONSCOREINSTALLER(unittest.TestCase):
    def setUp(self):

        self.installer = IconScoreInstaller('./')
        self.address = Address('cx', bytes.fromhex("1234123412341234123412341234123412341234"))
        self.package_path = './'
        self.archive_files('./', './test.zip')
        self.archive_path = "./test.zip"
        self.install_path = os.path.join(self.installer.icon_score_root_path, str(self.address))

    @staticmethod
    def archive_files(package_path: str, archive_path: str) -> bool:
        if os.path.isfile(package_path):
            print(f"{package_path} MUST be a directory. enter package path")
            return False
        flag = False
        with zipfile.ZipFile(archive_path, mode='a', compression=zipfile.ZIP_DEFLATED) as score_archive:
            for current_dir, dirs, files in os.walk(package_path):
                if current_dir.endswith('__pycache__'):
                    continue
                for file in files:
                    flag = True
                    if file.startswith('.'):
                        continue
                    if os.path.islink(file):
                        continue
                    score_archive.write(os.path.join(current_dir, file))
        if flag is False:
            os.remove(archive_path)
            return False
        return True

    def test_write_zipfile_with_bytes_case1(self):
        write_file_first_time_result = self.installer.\
            write_zipfile_with_bytes(self.install_path, self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertTrue(os.path.isfile(self.install_path))

        write_file_second_time_result = self.installer.\
            write_zipfile_with_bytes(self.install_path, self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_FILE_EXISTS_ERROR__CODE, write_file_second_time_result)

        self.installer.remove_exists_archive(self.install_path)

        write_file_with_exist_directory_path =\
            self.installer.write_zipfile_with_bytes('./'
                                                    , self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_IS_A_DIRECTORY_ERROR_CODE, write_file_with_exist_directory_path)

        write_file_with_unauthorized_path_result = \
            self.installer\
                .write_zipfile_with_bytes('/unauthorized', self.installer.read_zipfile_as_byte(self.archive_path))
        self.assertEqual(CONST_PERMISSION_ERROR_CODE, write_file_with_unauthorized_path_result)
        self.installer.remove_exists_archive(self.archive_path)

    def test_remove_exists_archive(self):
        self.installer.write_zipfile_with_bytes(self.install_path
                                                , self.installer.read_zipfile_as_byte(self.archive_path))
        self.installer.remove_exists_archive(self.install_path)
        self.assertFalse(os.path.isfile(self.install_path))
        self.installer.remove_exists_archive(self.archive_path)

    def test_extract_files(self):
        pass


if __name__ == "__main__":
    unittest.main()