from typing import List, Optional

from tools.precommit_converter.converter.convert_engine import ConvertedKeyValue
from tools.precommit_converter.extractor.extractor import IconServiceInfo


class Printer:
    def __init__(self, file_path: Optional[str] = None):
        self._file_path: Optional[str] = file_path

    def print(self, icon_service_info: Optional[IconServiceInfo], converted_kvs: List['ConvertedKeyValue']):
        if self._file_path is not None:
            pass

        if icon_service_info is not None:
            print(f"------------iconservice info-----------\n")
            print(icon_service_info)

        for ckv in converted_kvs:
            print(f"------------ {ckv.position}-----------\n"
                  f"TX Index ==> {ckv.tx_index} \n"
                  f"Key      ==> {ckv.key} \n"
                  f"Value    ==> {ckv.value}")
