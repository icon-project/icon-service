from typing import List, Optional

from tools.precommit_converter.converter.convert_engine import ConvertedKeyValue


class Printer:
    def __init__(self, file_path: Optional[str] = None):
        self._file_path: Optional[str] = file_path

    def print(self, converted_kvs: List['ConvertedKeyValue']):
        if self._file_path is not None:
            pass

        for ckv in converted_kvs:
            print(f"------------ {ckv.position}-----------\n"
                  f"TX Index ==> {ckv.tx_index} \n"
                  f"Key      ==> {ckv.key} \n"
                  f"Value    ==> {ckv.value}")

    def print_diff(self, left: List['ConvertedKeyValue'], right: List['ConvertedKeyValue']):
        pass
