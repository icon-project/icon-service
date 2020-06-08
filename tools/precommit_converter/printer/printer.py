from typing import List, Optional

from tools.precommit_converter.extractor.extractor import IconServiceInfo
from tools.precommit_converter.key_value import KeyValue


class Printer:
    def __init__(self, file_path: Optional[str] = None):
        self._file_path: Optional[str] = file_path

    def print(self, icon_service_info: Optional[IconServiceInfo], kvs: List['KeyValue']):
        if self._file_path is not None:
            pass

        print(f"* 'Hex:' means fail to convert. If new key, "
              f"value is defined on iconservice, you should supplement converter")

        if icon_service_info is not None:
            print(f"------------iconservice info-----------\n")
            print(icon_service_info)

        for i, kv in enumerate(kvs):
            print(f"------------{i}-----------\n"
                  f"TX Index    ==> {kv.tx_indexes} \n"
                  f"Key         ==> {kv.converted_key} \n"
                  f"Value       ==> {kv.converted_value} \n"
                  f"Bytes Key   ==> {kv.bytes_key} \n"
                  f"Bytes Value ==> {kv.bytes_value} \n")
