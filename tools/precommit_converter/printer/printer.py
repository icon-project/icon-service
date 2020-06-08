from typing import List, Optional

from tools.precommit_converter.extractor.extractor import IconServiceInfo
from tools.precommit_converter.key_value import KeyValue


class Printer:
    def __init__(self, file_path: Optional[str] = None, verbose: bool = False):
        self._file_path: Optional[str] = file_path
        self._verbose = verbose

    def print(self, icon_service_info: Optional[IconServiceInfo], kvs: List['KeyValue']):
        if self._file_path is not None:
            pass

        if icon_service_info is None:
            print("cannot find iconservice info from the file")
        else:
            print(icon_service_info)

        print(f"* 'Hex:' means fail to convert. If new key, "
              f"value is defined on iconservice, you should supplement converter")
        for i, kv in enumerate(kvs):
            print(f"------------{i}-----------\n"
                  f"TX Index    ==> {kv.tx_indexes} \n"
                  f"Key         ==> {kv.converted_key} \n"
                  f"Value       ==> {kv.converted_value}")
            if self._verbose:
                print(f"Bytes Key   ==> {kv.bytes_key} \n"
                      f"Bytes Value ==> {kv.bytes_value}")
