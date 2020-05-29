from collections import namedtuple
from typing import List, Tuple

BytesKeyValue = namedtuple("BytesKeyValue", ['tx_index', 'key', 'value'])


def extract_key_values_from_file(path: str) -> List['BytesKeyValue']:
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
            if line == "------------rc-precommit-data---------------\n":
                break
            sliced_str: list = line.split(" ")
            if sliced_str[0] == "TX:":
                tx_index = sliced_str[1]
            else:
                tx_index = None

            for i, string in enumerate(sliced_str):
                if string == "-":
                    key = sliced_str[i - 1]
                    value = sliced_str[i + 1]
                    if value[-1] == ",":
                        value = value[:len(value) - 1]
                    if value[:2] == "0x":
                        value = value[2:]
                    if tx_index is not None:
                        tx_index = int(tx_index)
                    key_values.append(BytesKeyValue(tx_index, bytes.fromhex(key), bytes.fromhex(value)))
    return key_values


