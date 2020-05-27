from typing import List, Optional

from tools.precommit_converter.convert_engine import ConvertedKeyValues


class Printer:
    def __init__(self, file_path: Optional[str] = None):
        self._file_path: Optional[str] = file_path

    def print(self, converted_kvs: List['ConvertedKeyValues']):
        if self._file_path is not None:
            pass

        for ckv in converted_kvs:
            print(f"----------index: {ckv.position}-----------\n"
                  f"Key   ==> {ckv.key} \n"
                  f"Value ==> {ckv.value}")

    def print_diff(self, left: List['ConvertedKeyValues'], right: List['ConvertedKeyValues']):
        pass
