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
            print("Cannot find iconservice info from the file")
        else:
            print(icon_service_info)

        print(f"* 'Hex:' means fail to convert. If new key, "
              f"value is defined on iconservice, you should supplement converter")
        prefix_format = "{:<12}==> {}"
        for i, kv in enumerate(kvs):
            print("--------------------------------[{:^3}]--------------------------------".format(i))
            print(prefix_format.format("TX Index", kv.tx_indexes))
            print(prefix_format.format("Key", kv.converted_key))
            print(prefix_format.format("Value", kv.converted_value))
            if self._verbose:
                print(prefix_format.format("Bytes Key", kv.bytes_key))
                print(prefix_format.format("Bytes Value", kv.bytes_value))
