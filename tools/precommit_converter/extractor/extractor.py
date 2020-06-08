import json
from typing import List, Tuple, Optional

from iconservice.base.block import Block
from tools.precommit_converter.key_value import KeyValue


class IconServiceInfo:
    def __init__(self,
                 version: str,
                 revision: int,
                 block: 'Block',
                 is_state_root_hash: str,
                 rc_state_root_hash: str,
                 state_root_hash: str,
                 prev_block_generator: Optional[str]):
        self.version = version
        self.revision = revision
        self.block = block
        self.is_state_root_hash = is_state_root_hash
        self.rc_state_root_hash = rc_state_root_hash
        self.state_root_hash = state_root_hash
        self.prev_block_generator = prev_block_generator

    def __str__(self):
        return str(self.__dict__)


class Extractor:

    @classmethod
    def extract(cls, path: str) -> Tuple[Optional[IconServiceInfo], List[KeyValue]]:
        # Check the txt format and extract the data from the
        if path.endswith("txt"):
            return cls._extract_key_values_from_text(path)
        elif path.endswith("json"):
            return cls._extract_key_values_from_json(path)
        else:
            raise Exception("Not Support file type")

    @classmethod
    def _extract_json(cls, path: str) -> dict:
        with open(path, 'r') as f:
            precommit_dict: dict = json.load(f)
        return precommit_dict

    @classmethod
    def _extract_key_values_from_json(cls, path: str) -> Tuple[IconServiceInfo, List[KeyValue]]:
        json_dict: dict = cls._extract_json(path)
        bytes_k_v: list = []
        block_batch = json_dict.get("blockBatch")

        if block_batch is None:
            raise KeyError("blockBatch not found")
        for data in block_batch:
            key, value = data["key"][2:], data["value"][2:]
            bytes_k_v.append(KeyValue(data["txIndexes"], bytes.fromhex(key), bytes.fromhex(value)))

        icon_service_info: 'IconServiceInfo' = IconServiceInfo(json_dict["iconservice"],
                                                               json_dict["revision"],
                                                               json_dict["block"],
                                                               json_dict["isStateRootHash"],
                                                               json_dict["rcStateRootHash"],
                                                               json_dict["stateRootHash"],
                                                               json_dict["prevBlockGenerator"])

        return icon_service_info, bytes_k_v

    @classmethod
    def _extract_key_values_from_text(cls, path: str) -> Tuple[None, List[KeyValue]]:
        """
        Extract key, value from the precommit text file
        If the format change, should fix this method
        :param path:
        :return:
        """
        key_values: list = []
        with open(path, "rt") as f:
            # Collect the key, values
            lines: List[str] = f.readlines()
            for line in lines:
                sliced_str: list = line.split(" ")
                for i, string in enumerate(sliced_str):
                    if string == "-":
                        key = sliced_str[i - 1]
                        value = sliced_str[i + 1]
                        if value[-1] == ",":
                            value = value[:len(value) - 1]
                        try:
                            key_values.append(KeyValue(None, bytes.fromhex(key), bytes.fromhex(value)))
                        except Exception as e:
                            break
        return None, key_values
