from typing import List, Tuple


def extract_key_values_from_file(path: str) -> List[Tuple[bytes, bytes]]:
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
                        key_values.append((bytes.fromhex(key), bytes.fromhex(value)))
                    except:
                        break
    return key_values
